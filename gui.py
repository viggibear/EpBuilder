import datetime
import os
import shutil
import sys

import networkx as nx
from PySide2.QtCore import QFile, QObject, Signal, Qt
from PySide2.QtGui import QDoubleValidator, QIntValidator, QPixmap, QBrush, QDropEvent, QIcon
from PySide2.QtUiTools import QUiLoader
from PySide2.QtWidgets import QApplication, QPushButton, QLineEdit, QComboBox, QCheckBox, QDialog, QLabel, QMenu, \
    QGraphicsView, QGraphicsScene, QFileDialog, QAction, QMainWindow, QMessageBox, QTableWidgetItem, QTableWidget, \
    QAbstractItemView, QVBoxLayout
from sympy import latex
from sympy.parsing.latex import parse_latex

from class_definitions import *


class MainWindow(QMainWindow):

    def __init__(self, ui_file, parent=None):
        super(MainWindow, self).__init__(parent)
        ui_file = QFile(ui_file)
        ui_file.open(QFile.ReadOnly)

        self.compartment_list = list()  # Empty compartment_list initialized
        self.variable_list = list()  # Empty variable list initialized
        self.simulation = None  # Simulation is generated after compilation
        self.substitutions = dict()  # Substitutions come from exec code

        loader = QUiLoader()
        loader.registerCustomWidget(
            QTableWidgetDragRows)  # Register custom QTableWidgetDragRows for Drag and Right-Click functions
        self.window = loader.load(ui_file)
        ui_file.close()

        plt.rc('text', usetex=True)  # set matplotlib options so that it uses LaTeX formatting
        plt.rc('font', family='serif')

        # Find buttons and link them to the respective functions, signals and options

        action_save_digraph = self.window.findChild(QAction, 'actionSaveDigraph')
        action_save_digraph.triggered.connect(self.save_digraph_event)

        action_save_plot = self.window.findChild(QAction, 'actionSavePlot')
        action_save_plot.triggered.connect(self.save_plot_event)

        add_compartment_button = self.window.findChild(QPushButton, 'AddCompartmentButton')
        add_compartment_button.clicked.connect(self.open_add_compartment_dialog)

        add_variable_button = self.window.findChild(QPushButton, 'AddVariableButton')
        add_variable_button.clicked.connect(self.open_add_variable_dialog)

        compile_button = self.window.findChild(QPushButton, 'CompileButton')
        compile_button.clicked.connect(self.compile)

        run_simulation_button = self.window.findChild(QPushButton, 'SimulateButton')
        run_simulation_button.clicked.connect(self.open_run_simulation)

        show_r0_button = self.window.findChild(QPushButton, 'R0Button')
        show_r0_button.clicked.connect(self.show_r0)

        self.compartment_table = self.window.findChild(QTableWidgetDragRows, 'CompartmentTable')
        self.compartment_table.setEditableInfectionState(True)
        self.compartment_table.delItem.connect(self.remove_item)
        self.compartment_table.editIS.connect(self.toggle_is)
        self.compartment_table.dropSignal.connect(self.drop_event)

        self.variable_table = self.window.findChild(QTableWidgetDragRows, 'VariableTable')
        self.variable_table.setDragEnabled(False)  # Set this table to be undraggable
        self.variable_table.delItem.connect(self.remove_item)

        self.vital_dynamics_checkbox = self.window.findChild(QCheckBox, 'VitalDynamicsCheckBox')
        self.vital_dynamics_checkbox.stateChanged.connect(self.vital_dynamics_toggle)

        self.diagram_view = self.window.findChild(QGraphicsView, 'DiagramView')  # Diagram for NetworkX Graph
        self.logging_view = self.window.findChild(QGraphicsView, 'LoggingView')  # Console for Logging progress

        self.timeLE = self.window.findChild(QLineEdit, 'TimeLE')
        self.timeLE.setValidator(QIntValidator())  # Validator to ensure only integers are placed in Time LineEdit

        self.window.setWindowIcon(QIcon(os.path.join('ui_files', 'icon.png')))  # Set the window icon
        self.window.show()

    """ Button functions open_add_compartment_dialog, open_add_variable_dialog, compile, open_run_simulation, show_r0"""

    def open_add_compartment_dialog(self):
        compartment_dialog = AddCompartment(os.path.join('ui_files', 'add_compartment_dialog.ui'), parent=self)
        compartment_dialog.add_compartment.connect(self.update_lists)

    def open_add_variable_dialog(self):
        variable_dialog = AddVariableWindow(os.path.join('ui_files', 'add_variable_dialog.ui'), self.compartment_list,
                                            parent=self)
        variable_dialog.add_variable.connect(self.update_lists)

    def compile(self):
        # Pull changes made in compartment_table's value column
        new_ordered_list = list()
        for row in range(self.compartment_table.rowCount()):
            for compartment in self.compartment_list:
                if compartment.name == self.compartment_table.item(row, 0).text():
                    cell_text = self.compartment_table.item(row, 2).text()
                    if cell_text != "":
                        try:
                            compartment.value = float(self.compartment_table.item(row, 2).text())
                        except ValueError:
                            pass
                    else:
                        compartment.value = 0
                    new_ordered_list.append(compartment)
        self.compartment_list = new_ordered_list

        # Remove variables inside variable_list if compartment doesn't exist
        new_ordered_list = list()
        for variable in self.variable_list:
            if (variable.origin in self.compartment_list or variable.origin is None) and (
                    variable.end in self.compartment_list or variable.end is None):
                new_ordered_list.append(variable)
        self.variable_list = new_ordered_list

        for compartment in self.compartment_list:
            compartment.set_change_function(self.variable_list,
                                            self.compartment_list)  # Set the change functions of each compartment

        self.simulation = Simulation(self.compartment_list)  # Set self.simulation
        self.window.findChild(QPushButton, 'ShowGraphButton').clicked.connect(
            self.simulation.show_graph)  # Set Show_Graph Button
        self.update_visuals()  # Update Tables and NetworkX Graph

    def open_run_simulation(self):
        self.compile()  # Compile first

        variable_set = set()
        for variable in self.variable_list:  # Group into a set all symbols used in all terms in global_variable_list
            for term in variable.equation.free_symbols:
                variable_set.add(term)
        for compartment in self.compartment_list:  # Remove all compartment symbols from variable_set
            if compartment.symbol in variable_set:
                variable_set.remove(compartment.symbol)

        # Set the correct substitution dictionary
        substitution_dictionary = dict()
        for substitution in variable_set:
            try:
                substitution_dictionary[substitution] = self.substitutions[
                    substitution]  # Check if substitution already exists
            except KeyError:
                substitution_dictionary[substitution] = 0

        if self.compartment_list == list():
            QMessageBox.critical(self.window, "Run Simulation Error",
                                 "Simulation cannot be run as no Compartments have been added")
            return
        elif self.variable_list == list():
            QMessageBox.critical(self.window, "Error", "Simulation cannot be run as no Variables have been added")
            return

        # Open dialog so substitutions can be set
        set_substitutions_dialog = SetSubstitutionsWindow(substitution_dictionary)
        set_substitutions_dialog.set_substitutions.connect(self.update_substitutions)
        set_substitutions_dialog.exec_()

        # Get new Substitutions and run simulation
        self.simulation.substitutions = self.substitutions
        self.simulation.set_plot(simulation_time=int(self.timeLE.text()), display_output=False)
        self.update_visuals()

        self.update_console("{} time units of simulation completed for Model. Press 'Show Graph' to see output.".format(
            self.timeLE.text()))

    def show_r0(self):
        self.compile()  # Compile first

        # Catch common errors that imply that R0 cannot be calculated --> maybe find a more direct way to check?
        try:
            r0_formula = self.simulation.calculate_r0()
        except AttributeError:
            self.update_console("R0 could not be calculated for your model.")
            return
        except TypeError:
            self.update_console("R0 could not be calculated for your model.")
            return
        except IndexError:
            self.update_console("R0 could not be calculated for your model.")
            return

        self.update_console('R0 calculated: {}     ||TeX:    {}'.format(r0_formula, latex(r0_formula)))

        # Open Matplotlib window to display R0 in LaTeX
        plt.figure(num='Basic Reproductive Number')
        plt.text(0.35, 0.5, r'$R_0$ is ' + "${}$".format(latex(r0_formula)), dict(size=30, ma='center'))
        plt.axis('off')  # Don't show xy axis
        plt.show()

    def update_visuals(self):
        """
        This function updates compartment_table, variable_table and also the NetworkX Graph displayed
        """
        # Update compartment_table by iterating through compartment_list
        self.compartment_table.setRowCount(len(self.compartment_list))
        for index, compartment in enumerate(self.compartment_list):
            self.compartment_table.setItem(index, 0, self.get_uneditable_table_widget_item(compartment.name,
                                                                                           compartment.infection_state))
            self.compartment_table.setItem(index, 1, self.get_uneditable_table_widget_item(compartment.symbol))
            self.compartment_table.setItem(index, 2, QTableWidgetItem(f'{compartment.value:.4f}'))  # 3rd column acc 4dp

        # Update variable_table by iterating through variable_list
        self.variable_table.setRowCount(len(self.variable_list))
        for index, variable in enumerate(self.variable_list):
            self.variable_table.setItem(index, 0, self.get_uneditable_table_widget_item(variable.equation))
            self.variable_table.setItem(index, 1, self.get_uneditable_table_widget_item(
                str(variable.origin.name) if variable.origin is not None else "-"))  # Birth is a -
            self.variable_table.setItem(index, 2, self.get_uneditable_table_widget_item(
                str(variable.end.name) if variable.end is not None else "-"))  # Death is a -

        # Create NetworkX graph
        G = nx.DiGraph()
        edges = list()
        labels = dict()
        for variable in self.variable_list:  # Set labels = {[Source Node1, End Node1]: Latex Equation1, ...}
            se_list = [variable.origin.name if variable.origin is not None else 'Birth',
                       variable.end.name if variable.end is not None else 'Death']
            edges.append(se_list)
            labels[tuple(se_list)] = "${}$".format(latex(variable.equation))

        G.add_edges_from(edges)
        pos = nx.planar_layout(G)  # Planar layout so edges do not collide
        plt.figure()  # Start a figure before drawing
        nx.draw(G, pos, edge_color='black', node_size=2000, node_shape='s', node_color='white', with_labels=True,
                style='bold')
        nx.draw_networkx_edge_labels(G, pos, edge_labels=labels)
        plt.savefig('graph.png')  # Save as graph.png so QPixmap can be created from it below
        plt.close()  # Close plt to save memory and prevent issues downline

        scene = QGraphicsScene()
        scene.addPixmap(QPixmap('graph.png'))
        self.diagram_view.setScene(scene)  # DiagramView is set to be the graph.png
        self.diagram_view.show()

    def update_console(self, text):
        """
        This function updates logging_view with the given text, but has to do it in quite a roundabout way because
        I had to use a QGraphicsScene for this to allow for scrolling

        :param text: String that is updated in the console
        """
        current_text = self.logging_view.scene().items()[
            0].toPlainText() if self.logging_view.scene() is not None else ''
        current_text += '[{}] {}\n'.format(datetime.datetime.now().strftime('%X'), text)
        new_scene = QGraphicsScene()
        x = new_scene.addText(current_text)
        x.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.logging_view.setScene(new_scene)

    """ Signal Functions update_lists, update_substitutions, remove_item, toggle_is, drop_event"""

    def update_lists(self, item):
        if type(item) == Variable:
            self.variable_list.append(item)
        if type(item) == Compartment:
            self.compartment_list.append(item)
        self.update_visuals()

    def update_substitutions(self, item):
        self.substitutions = item

    def remove_item(self, params):
        if params[0] == 'VariableTable':
            del self.variable_list[params[1]]
        if params[1] == 'CompartmentTable':
            del self.compartment_list[params[1]]
        self.compile()  # If only update_visuals are called, items will not be deleted

    def toggle_is(self, params):
        if params[0] == 'CompartmentTable':
            self.compartment_list[params[1]].infection_state = not self.compartment_list[params[1]].infection_state
        self.update_visuals()

    def drop_event(self, params):
        if params[0] == 'CompartmentTable':
            # Pull changes made in compartment_table to the order or values of each compartment
            new_ordered_list = list()
            for row in range(self.compartment_table.rowCount()):
                for compartment in self.compartment_list:
                    if compartment.name == self.compartment_table.item(row, 0).text():
                        cell_text = self.compartment_table.item(row, 2).text()
                        if cell_text != "":
                            try:
                                compartment.value = float(self.compartment_table.item(row, 2).text())
                            except ValueError:
                                pass
                        else:
                            compartment.value = 0
                        new_ordered_list.append(compartment)
            self.compartment_list = new_ordered_list
        self.update_visuals()

    def vital_dynamics_toggle(self):
        #  Compile Vital Dynamics terms and ensure no double adding by clearing vital
        vital_dynamics_variables = list()
        mu, tau = sym.symbols('mu tau', nonnegative=True)
        for index, compartment in enumerate(self.compartment_list):
            if index == 0:
                vital_dynamics_variables.append(Variable(tau, None, compartment, is_vital_dynamics=True))
            vital_dynamics_variables.append(
                Variable(mu * compartment.symbol, compartment, None, is_vital_dynamics=True))

        self.variable_list = [variable for variable in self.variable_list if
                              not variable.is_vital_dynamics]  # Remove all vital dynamics terms
        if self.vital_dynamics_checkbox.isChecked():
            self.variable_list.extend(vital_dynamics_variables)  # Add Vital Dynamics if qCheckBox is ticked

        self.update_visuals()

    """ Save Functions save_digraph_event and save_plot_event"""

    def save_digraph_event(self):
        if self.variable_list == list():
            QMessageBox.warning(self.window, "Save DiGraph Error", "Cannot save DiGraph as there are no Variables")
            return
        path_to_file, _ = QFileDialog.getSaveFileName(self.window, self.tr("Load Image"), self.tr("~/Desktop/"),
                                                      self.tr("Images (*.png)"))  # Open FileDialog and get link
        shutil.move('graph.png', path_to_file)  # Move graph.png to path specified
        self.update_console('DiGraph image has been saved under {}'.format(path_to_file))

    def save_plot_event(self):
        try:
            output_dataframe = self.simulation.get_dataframe()
        except AttributeError:  # If Simulation has not been run yet, throw a Warning Message
            QMessageBox.warning(self.window, "Save Plot Error", "Please ensure that you have run your simulation")
            return
        except IndexError:
            QMessageBox.warning(self.window, "Save Plot Error", "Please ensure that you have run your simulation")
            return
        path_to_file, _ = QFileDialog.getSaveFileName(self.window, self.tr("Load Image"), self.tr("~/Desktop/"),
                                                      self.tr("Comma Separated Values File (*.csv)"))  # Get link

        output_dataframe.to_csv(path_to_file, index=None)  # Output the csv as to path specified using pandas
        self.update_console('Simulation Data has been saved under {}'.format(path_to_file))

    @staticmethod
    def get_uneditable_table_widget_item(in_object, is_inf=False):
        """

        :param in_object:  String to display
        :param is_inf: if infection_state is True, cell will be red
        :return: QTableWidgetItem that can be used in compartment_table or variable_table
        """
        out_item = QTableWidgetItem(str(in_object))
        out_item.setFlags(Qt.ItemIsEnabled)
        if is_inf:
            out_item.setBackground(QBrush(Qt.red))
        return out_item


class AddCompartment(QObject):
    add_compartment = Signal(Compartment)

    def __init__(self, ui_file, parent=None):
        super(AddCompartment, self).__init__(parent)
        ui_file = QFile(ui_file)
        ui_file.open(QFile.ReadOnly)

        self.window = QUiLoader().load(ui_file)

        add_button = self.window.findChild(QPushButton, 'AddButton')
        add_button.clicked.connect(self.on_add_clicked)

        self.nameLE = self.window.findChild(QLineEdit, 'NameLE')
        self.symbolLE = self.window.findChild(QLineEdit, 'SymbolLE')
        self.initLE = self.window.findChild(QLineEdit, 'InitLE')
        self.infectionStateCheckBox = self.window.findChild(QCheckBox, 'InfectionStateCheckBox')

        # Add Constraints
        self.initLE.setValidator(QDoubleValidator())
        self.nameLE.setMaxLength(32)
        self.symbolLE.setMaxLength(32)
        self.initLE.setMaxLength(16)

        self.window.setWindowIcon(QIcon(os.path.join('ui_files', 'icon.png')))  # Set the window icon
        self.window.show()

    def on_add_clicked(self):
        new_compartment = Compartment(name=str(self.nameLE.text()),
                                      symbol=sym.symbols(str(self.symbolLE.text())),
                                      value=float(self.initLE.text()),
                                      infection_state=True if self.infectionStateCheckBox.isChecked() else False)

        self.add_compartment.emit(new_compartment)
        self.window.destroy()


class AddVariableWindow(QObject):
    add_variable = Signal(Variable)

    def __init__(self, ui_file, compartment_list, parent=None):
        super(AddVariableWindow, self).__init__(parent)
        ui_file = QFile(ui_file)
        ui_file.open(QFile.ReadOnly)

        self.window = QUiLoader().load(ui_file)

        add_button = self.window.findChild(QPushButton, 'AddButton')
        add_button.clicked.connect(self.on_add_clicked)

        self.compartment_list = compartment_list
        self.origin_combobox = self.window.findChild(QComboBox, 'OriginComboBox')
        self.destination_combobox = self.window.findChild(QComboBox, 'DestinationComboBox')
        for compartment in compartment_list:
            self.origin_combobox.addItem(compartment.name)
            self.destination_combobox.addItem(compartment.name)
        self.origin_combobox.addItem('Birth')
        self.destination_combobox.addItem('Death')

        self.window.setWindowIcon(QIcon(os.path.join('ui_files', 'icon.png')))  # Set the window icon
        self.window.show()

    def on_add_clicked(self):
        equationLE = self.window.findChild(QLineEdit, 'EquationLE')
        descriptionLE = self.window.findChild(QLineEdit, 'DescriptionLE')

        try:
            origin = self.compartment_list[self.origin_combobox.currentIndex()]
        except IndexError:
            origin = None

        try:
            end = self.compartment_list[self.destination_combobox.currentIndex()]
        except IndexError:
            end = None

        if origin == end and origin is None:  # Both are None
            QMessageBox.critical(self.window, "Error", "Origin and End cannot be Birth and Death")
            return
        elif origin == end:  # Both are the same but not None
            QMessageBox.critical(self.window, "Error", "Origin and End cannot be the same")
            return

        new_variable = Variable(equation=parse_latex(str(equationLE.text())).simplify(),
                                origin=origin,
                                end=end,
                                description=str(descriptionLE.text()))

        self.add_variable.emit(new_variable)
        self.window.destroy()


class SetSubstitutionsWindow(QDialog):
    set_substitutions = Signal(dict)

    def __init__(self, substitution_dict, parent=None):
        super(SetSubstitutionsWindow, self).__init__(parent)
        self.valueLE_list = list()
        self.variable_dict = substitution_dict
        layout = QVBoxLayout()
        # Create the respective LineEdits so we can edit the substitution values
        for key, value in substitution_dict.items():
            varLabel = QLabel(str(key))
            varLE = QLineEdit(str(value))
            varLE.setValidator(QDoubleValidator())  # Only doubles accepted
            self.valueLE_list.append(varLE)
            layout.addWidget(varLabel)
            layout.addWidget(varLE)

        # Run to emit subsitutions_dict
        run_button = QPushButton("Run")
        layout.addWidget(run_button)
        run_button.clicked.connect(self.on_run_clicked)

        self.setLayout(layout)
        self.setWindowIcon(QIcon(os.path.join('ui_files', 'icon.png')))  # Set the window icon
        self.setWindowTitle("Set Substitutions")  # Set the window title

    def on_run_clicked(self):
        value_list = list()
        #  Collect entered values and package it as a dictionary
        for line_edit in self.valueLE_list:
            value_list.append(float(line_edit.text()))
        self.set_substitutions.emit(dict(zip(self.variable_dict.keys(), value_list)))
        self.accept()


class QTableWidgetDragRows(QTableWidget):
    delItem = Signal(list)
    editIS = Signal(list)
    dropSignal = Signal(list)

    def __init__(self, *args, **kwargs):
        """
        This custom class that expands on QTableWidget is created just to ensure that rows can be dragged around

        """
        super().__init__(*args, **kwargs)

        self.deletable = True
        self.infectionStateEditable = False

        self.setDragEnabled(True)
        self.setAcceptDrops(True)
        self.setDeletable(True)
        self.viewport().setAcceptDrops(True)
        self.setDragDropOverwriteMode(False)
        self.setDropIndicatorShown(True)

        self.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.setDragDropMode(QAbstractItemView.InternalMove)

        self.customContextMenuRequested.connect(self.contextMenuEvent)

    def dropEvent(self, event: QDropEvent):
        if not event.isAccepted() and event.source() == self:
            drop_row = self.drop_on(event)

            rows = sorted(set(item.row() for item in self.selectedItems()))
            rows_to_move = [
                [QTableWidgetItem(self.item(row_index, column_index)) for column_index in range(self.columnCount())]
                for row_index in rows]
            for row_index in reversed(rows):
                self.removeRow(row_index)
                if row_index < drop_row:
                    drop_row -= 1

            for row_index, data in enumerate(rows_to_move):
                row_index += drop_row
                self.insertRow(row_index)
                for column_index, column_data in enumerate(data):
                    self.setItem(row_index, column_index, column_data)
            event.accept()
            for row_index in range(len(rows_to_move)):
                self.item(drop_row + row_index, 0).setSelected(True)
                self.item(drop_row + row_index, 1).setSelected(True)
        super().dropEvent(event)
        self.dropSignal.emit([self.objectName()])

    def drop_on(self, event):
        index = self.indexAt(event.pos())
        if not index.isValid():
            return self.rowCount()

        return index.row() + 1 if self.is_below(event.pos(), index) else index.row()

    def is_below(self, pos, index):
        rect = self.visualRect(index)
        margin = 2
        if pos.y() - rect.top() < margin:
            return False
        elif rect.bottom() - pos.y() < margin:
            return True
        # noinspection PyTypeChecker
        return rect.contains(pos, True) and not (int(self.model().flags(index)) & Qt.ItemIsDropEnabled) and pos.y()

    def contextMenuEvent(self, pos):
        menu = QMenu()
        if self.deletable is True:
            delete_action = menu.addAction("Delete")
        else:
            delete_action = None

        if self.infectionStateEditable is True:
            edit_infection_state_action = menu.addAction("Toggle Infection State")
        else:
            edit_infection_state_action = None

        global_position = self.mapToGlobal(pos)
        selected_item = menu.exec_(global_position)

        if selected_item == delete_action and self.deletable:
            action_row = self.itemAt(pos).row()
            self.removeRow(action_row)
            self.delItem.emit([self.objectName(), action_row])
        if selected_item == edit_infection_state_action:
            action_row = self.itemAt(pos).row()
            self.editIS.emit([self.objectName(), action_row])

    def setDeletable(self, param):
        self.deletable = param if param in [True, False] else False

    def setEditableInfectionState(self, param):
        self.infectionStateEditable = param if param in [True, False] else False


if __name__ == "__main__":
    app = QApplication(sys.argv)
    form = MainWindow(os.path.join('ui_files', 'main_window.ui'))
    sys.exit(app.exec_())
