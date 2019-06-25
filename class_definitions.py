import random
import time

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import sympy as sym
from scipy.integrate import odeint


class Simulation:
    COLOUR_LIST = ['#e6194B', '#3cb44b', '#aa8736', '#4363d8', '#f58231', '#911eb4', '#42d4f4', '#f032e6', '#bfef45',
                   '#fabebe', '#469990', '#e6beff', '#9A6324', '#800000', '#aaffc3', '#808000', '#ffd8b1', '#000075',
                   '#a9a9a9', '#ffffff']

    def __init__(self, compartment_list, substitutions=None):
        """

        :param compartment_list: List of compartments to run in the simulation
        """
        self.compartment_list = compartment_list
        self.substitutions = substitutions if substitutions is not None else dict()

    def getFVG(self):
        """

        :param compartment_list: List of compartments

        :return: (F, V, G) where F (new infections), V (transfer infections) of size (fn_list, 1) and G (next gen matrix) of
        :size (fn_list, fn_list)

        For more notes on how to this is done, please refer to
        Further Notes on the Basic Reproduction Number by (van den Driessche and Watmough, 2008)
        """

        # Extract into i_list the symbols of the compartments that are
        # considered carriers of the disease (Exposed/Infected etc.) and their respective DEs into fn_list
        i_list = list()
        fn_list = list()
        for compartment in self.compartment_list:
            if compartment.infection_state:
                i_list.append(compartment.symbol)
                fn_list.append(compartment.change_function)

        # We need to compile the individual terms as positive and negative separately and
        # also a master list of negative terms since negative terms are 'transfer' (V) terms
        dict_list = []
        negative_term_list = []  # compile negative terms
        for i in fn_list:
            variable_dict = {'pos': [], 'neg': []}  # Create 2 dictionaries, positive and negative
            for j in i.args:
                # check and append to respective list
                if j.args[0] == -1:  # Check if term is negative by splitting args
                    variable_dict['neg'].append(-j)
                    negative_term_list.append(-j)
                else:
                    variable_dict['pos'].append(j)
            dict_list.append(variable_dict)  # add split dictionary to the main list

        # instantiate zeros matrix for F (new infections) and V (transfer infections)
        F = sym.zeros(len(i_list), 1)
        V = sym.zeros(len(i_list), 1)

        for index, variable_dict in enumerate(dict_list):  # iterate through dictionary_list
            for term in variable_dict['pos']:  # looking at positive terms first to determine if F or V
                if term not in negative_term_list:  # if not found as a negative term, add it to the F matrix
                    F[index, 0] += term
                else:  # term is a V term
                    V[index, 0] -= term
            for term in variable_dict['neg']:  # negative terms are automatically added to V matrix
                V[index, 0] += term
        G = F.jacobian(i_list) * (
                V.jacobian(i_list) ** -1)  # Get the next-gen-matrix by taking the 2 jacobians and FV^-1
        return F, V, G

    def calculate_r0(self):
        """
        Calculates the symbolic formula for R0 with its own compartment_list

        :return: formula for R0
        """
        g = self.getFVG()[2]  # Get Next Gen Matrix from getFVG function
        r0 = sorted(g.eigenvals().keys(), key=sym.default_sort_key)[-1]  # sort by default and take largest eigenvalue
        return r0

    def show_graph(self):
        """
        Sets up the graph and plot

        """
        time_length = self.compartment_list[0].plot.shape[0]
        timespace = np.linspace(0, time_length, time_length)  # Set timespace

        window_title = "{} model simulation - {} time units".format(
            str([compartment.symbol for compartment in self.compartment_list]), time_length)
        fig = plt.figure(window_title, facecolor='w')
        ax = fig.add_subplot(111, axisbelow=True)
        for index, compartment in enumerate(self.compartment_list):
            if compartment.plot is None:  # Check if plot is not empty before plotting, else raise error
                raise Exception('Plot of {} is empty'.format(compartment.name))
            try:
                ax.plot(timespace, compartment.plot, self.COLOUR_LIST[index], alpha=0.5, lw=2,
                        label=compartment.name)  # Get a colour from above and plot the graph
            except IndexError:  # Except if all colours are used up, get a random colour instead
                ax.plot(timespace, compartment.plot, "#{:06x}".format(random.randint(0, 0xFFFFFF)), alpha=0.5, lw=2,
                        label=compartment.name)

        ax.set_xlabel('Time /days')
        ax.set_ylabel('Number (1000s)')
        ax.set_ylim(0, 1.2)
        ax.yaxis.set_tick_params(length=0)
        ax.xaxis.set_tick_params(length=0)
        ax.grid(b=True, which='major', c='w', lw=2, ls='-')
        legend = ax.legend()
        legend.get_frame().set_alpha(0.5)
        for spine in ('top', 'right', 'bottom', 'left'):
            ax.spines[spine].set_visible(False)
        plt.title(window_title)
        plt.show()

    def get_dataframe(self):
        """

        :return: pandas.DataFrame with Time as first column and subsequent columns being the plot of each compartment
        """
        time_length = self.compartment_list[0].plot.shape[0]
        timespace = np.linspace(0, time_length, time_length)  # Set timespace

        dataframe_dict = dict()

        dataframe_dict['Time'] = timespace

        for compartment in self.compartment_list:
            dataframe_dict[compartment.name] = compartment.plot

        return pd.DataFrame(dataframe_dict)

    def set_plot(self, simulation_time=200, verbose=False, display_output=True):
        """

        :param simulation_time: Length to run solve (default 200 days)
        :param verbose: (default False)
        :param display_output: show matplot of the simulation (default True)

        Compute the plot of each compartment based on the specified timespace

        """

        timespace = np.linspace(0, simulation_time, simulation_time)  # Define the time-space as a numpy vector

        y = list()
        for compartment in self.compartment_list:
            y.append(compartment.value)

        substitution_function = self.get_lambda_function()

        def deriv(y, t):
            dv = []
            for index, compartment in enumerate(self.compartment_list):
                compartment.value = y[index]
                subs = substitution_function(self, t)
                dv.append(compartment.compute_change_function(**subs))
                if verbose and random.random() < 0.01:
                    print('{} has been calculated to be {} at {}'.format(compartment.name, compartment.value, t))
            return dv

        # Time this function so the user knows how long the simulation took to run
        start_time = time.time()
        ret = odeint(deriv, y0=y, t=timespace, mxstep=5000000)
        end_time = time.time()
        print("{} time units of simulation completed for model within {} seconds".format(simulation_time,
                                                                                         end_time - start_time))

        for index, compartment in enumerate(self.compartment_list):
            compartment.plot = ret.T[index]

        if display_output:
            self.show_graph()

    def get_lambda_function(self):
        """
        :return: lambda function that is used for Compartment.compute_change_function
        """

        dict_string = ""
        for index, compartment in enumerate(self.compartment_list):
            dict_string += "\'{}\'".format(str(compartment.symbol)) + ": "
            dict_string += "self.compartment_list[{}].value, ".format(index)
        for substitution, value in self.substitutions.items():
            dict_string += "\'{}\'".format(substitution) + ": "
            dict_string += '{}, '.format(value)
        code = """lambda self, t: {%s}""" % dict_string
        return eval(code)


class Compartment:

    def __init__(self, name, symbol, variable_list=None, change_function=0, infection_state=False,
                 compute_change_function=0, value=0, plot=None):
        """

        :param name: string name of the compartment
        :param symbol: SymPy symbol of the compartment
        :param variable_list: List of variables in the compartment
        :param change_function: DE of compartment
        :param infection_state: set to True if this compartment is considered a carrier of the disease
        :param compute_change_function: Lambdified function from change function
        :param value: numerical value of component
        :param plot: plot of component calculated after simulation

        """
        self.name = name
        self.symbol = symbol
        self.variable_list = variable_list if variable_list is not None else list()
        self.change_function = change_function
        self.infection_state = infection_state
        self.compute_change_function = compute_change_function
        self.value = value
        self.plot = plot

    def set_change_function(self, global_variable_list, global_compartment_list):
        """

        :param global_variable_list: list of all variables in the DEs

        Correctly assigns terms to the compartment's own DE depending on the variable's origin and end

        """
        self.variable_list = list()  # Refresh self.variable_list and self.change_function
        self.change_function = 0

        variable_set = set()
        for variable in global_variable_list:  # Group into a set all symbols used in all terms in global_variable_list
            for term in variable.equation.free_symbols:
                variable_set.add(term)
        for compartment in global_compartment_list:
            variable_set.add(compartment.symbol)

        for variable in global_variable_list:
            if variable.origin == self:
                self.variable_list.append(-variable.equation)
            elif variable.end == self:
                self.variable_list.append(variable.equation)
        for variable_equation in self.variable_list:
            self.change_function += variable_equation
        try:
            self.compute_change_function = sym.lambdify(variable_set, self.change_function,
                                                        'numpy')
        except AttributeError:
            raise Exception('Ensure the change_function of compartment {} is defined symbolically'.format(self.name))


class Variable:
    def __init__(self, equation, origin, end, is_vital_dynamics=False, description=None):
        """

        :param equation: SymPy equation
        :param origin: compartment the term subtracts from
        :param end: compartment the term adds to
        :param is_vital_dynamics: vital dynamics, tau for birthrate and mu for death rate
        :param description: Describes the Term and its derivation (optional)

        """
        self.equation = equation
        self.origin = origin
        self.end = end
        self.is_vital_dynamics = is_vital_dynamics
        self.description = description


""" GUI DEFINITIONS BELOW """
