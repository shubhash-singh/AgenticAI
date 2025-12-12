# Visual Concept
The simulation will depict two distinct regions (e.g., circles or rectangular boxes) representing objects with different initial temperatures. A visual indicator of heat flow (e.g., animated arrows or particles) will emerge from the hotter region and move towards the colder region. The visual will also incorporate a thermometer displaying the temperature of each region, and these readings will change dynamically as heat transfers.

# Draggable Elements
1. Hotter Object: (Center of SVG), controls its position and proximity to the colder object.
2. Colder Object: (Center of SVG), controls its position and proximity to the hotter object.

# Sliders (exactly 2)
1. Initial Temperature Difference: min=[10], max=[100], default=[40], controls the starting temperature difference between the two objects.
2. Heat Transfer Rate: min=[0.1], max=[2.0], default=[1.0], controls the speed at which heat flows between the objects.

# State Variables
- Temperature_Hotter: The current temperature of the hotter object.
- Temperature_Colder: The current temperature of the colder object.
- Thermal Equilibrium: A boolean flag indicating if both objects have reached the same temperature.

# Visual Changes on Interaction
- When Initial Temperature Difference slider is adjusted: The initial values of Temperature_Hotter and Temperature_Colder are updated. The visual representation of temperature (e.g., color intensity) will change accordingly.
- When Heat Transfer Rate slider is adjusted: The speed of the animated heat flow indicators will increase or decrease.
- When Temperature_Hotter and Temperature_Colder become equal: The animated heat flow indicators will cease to move, and the Thermal Equilibrium flag will be set to true. The visual might display a subtle "equilibrium" indicator.

# Interaction Flow
1. User drags the "Hotter Object" and "Colder Object" to desired positions within the simulation window.
2. User adjusts the "Initial Temperature Difference" slider to set the starting temperatures of the objects. The visual display of temperatures updates.
3. User adjusts the "Heat Transfer Rate" slider to control the speed of heat flow. Animated arrows/particles begin to move from the hotter to the colder object.
4. The temperatures of both objects change dynamically. The animated heat flow continues until thermal equilibrium is reached, at which point the flow stops.

# Quiz Questions
1. Q: Heat always flows from:
   A: A hotter object to a colder object.
   Explanation: This is the fundamental principle of heat transfer; energy naturally moves from regions of higher concentration (hotter) to lower concentration (colder).
2. Q: What does the "Thermal Equilibrium" state represent in this simulation?
   A: The point where both objects have reached the same temperature.
   Explanation: When two objects are in thermal equilibrium, there is no net flow of heat between them because their temperatures are equal.