
# EpBuilder - WYSIWYG Compartmental Epidemiology Model Builder

EpBuilder is a beautiful Compartmental Epidemiology Builder that can quickly prototype models and simulate them based on parameters you input

![Main GUI for EpBuilder](https://i.imgur.com/PjMH9wZ.png)

# Running EpBuilder
Usage requirements: (also found in `requirements.txt`)

 1. matplotlib (for plotting and LaTeX rendering)
 2. networkx (to draw Simulation DiGraph)
 3. numpy (to handle Jacobian Matrices and other functions for both symbolic and normal computation)
 4. pandas (to handle DataFrames for csv output)
 5. PySide2 (GUI framework)
 6. scipy (odeint function to simulate the Differential Equations)
 7. sympy (library for symbolic computation)
 
Once all requirements have been installed through `pip install -r requirements.txt`, double click `gui.py`to run EpBuilder


# Usage Guide


## Adding Compartments and Variables
You can add compartments and variables (using [LaTeX](http://meta.math.stackexchange.com/questions/5020/mathjax-basic-tutorial-and-quick-reference)) with the simple GUI

Select "Infection State" if the compartment is considered *infectious* to help in the calculation of R<sub>0</sub> 

![enter image description here](https://i.imgur.com/robhlnW.png) 		![enter image description here](https://i.imgur.com/wXW4a1u.png)

## Running Simulations
Press 'Run Simulation' and key in your substitutions, then click run - the logger in the main window will be updated once the simulation is run

![enter image description here](https://i.imgur.com/J7B4m99.png)

 ### To view output:
 - Click 'Show Graph' to see the visual output of your simulation
![enter image description here](https://i.imgur.com/yFFFcXr.png)
 - Go to File→Save Simulation Output to export the simulation output to a *.csv* file
 
	 ![enter image description here](https://i.imgur.com/9ZEJWCS.png)

## Vital Dynamics

EpBuilder can quickly add and remove vital dynamics (τ *birth*) and (μ *death*) to your model by toggling a single checkbox

![enter image description here](https://i.imgur.com/bUObG62.png)

## Calculating Basic Reproductive Number - R<sub>0</sub>

EpBuilder can also automatically calculate R<sub>0</sub> for you based on your model by considering which states are considered infectious (highlighted in red) under the Compartment Table. Click 'Show R<sub>0</sub> Formula' to see a matplotlib dialog with the formula or look in the logging console for the Plaintext and TeX output. 

You may right click the Compartment Table to toggle the 'Infection State' option.
![enter image description here](https://i.imgur.com/242AZHG.png?1)

A few examples of some calculations based on [these](https://web.stanford.edu/~jhj1/teachingdocs/Jones-on-R0.pdf) [papers](https://server.math.umanitoba.ca/~jarino/yaounde2009/Watmough_R0.pdf) are shown below.

### 1. Basic SIR model
![enter image description here](https://i.imgur.com/gweg3ti.png)![enter image description here](https://i.imgur.com/FPDHRWC.png)

### 2. SIR model with vital dynamics
![enter image description here](https://i.imgur.com/9mNC75z.png)![enter image description here](https://i.imgur.com/e4VmLsy.png)

### 3. SEIR model with vital dynamics
![enter image description here](https://i.imgur.com/oMEJV0J.png)
![enter image description here](https://i.imgur.com/cx0CFTd.png)

## Addendum

### Controlling order of Compartments to adjust Vital Dynamics
You can rearrange the Compartment Table to change where Vital Dynamics are added. 
![enter image description here](https://i.imgur.com/eEToRdc.png?1)![enter image description here](https://i.imgur.com/oZiTl9k.png?1)

By Default, only the 1st compartment gets 'birth' (τ) while every compartment gets 'death' (μ * Compartment Symbol)

### Changing the value of Compartments after Simulation
Double Click the current value cells in the Compartment Table to change the current value of any Compartment.
![enter image description here](https://i.imgur.com/WuNONIr.png)
