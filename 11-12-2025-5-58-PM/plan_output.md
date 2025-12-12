# Visual Concept
The main visualization will depict two distinct regions, representing two objects with initially different temperatures. One object (e.g., a red circle) will be hotter, and the other (e.g., a blue circle) will be colder. Arrows will visually represent the flow of heat from the hotter object to the colder object. As heat flows, the temperature indicators of both objects will change, and the intensity of the arrows will adjust dynamically. A thermometer will also be present, showing the temperature of the currently selected object.

# SVG Layout (500x350 viewBox)
- Main elements:
    - Two circles: `cx="150" cy="200"` (object A, red), `cx="350" cy="200"` (object B, blue). Radius of 50 for both.
    - Two temperature indicator bars within each circle: `x="120" y="170"` for A, `x="320" y="170"` for B. Width of 60, height of 20.
    - A thermometer shape: `x="240" y="150" width="20" height="100"`.
    - Heat flow arrows: Multiple arrow elements dynamically positioned and scaled between the circles.
- Color scheme:
    - Hot object (A): Red (#FF0000) and its temperature indicator a darker shade of red.
    - Cold object (B): Blue (#0000FF) and its temperature indicator a darker shade of blue.
    - Heat flow arrows: Orange (#FFA500), varying in intensity.
    - Thermometer: White (#FFFFFF) with a red mercury line.
- Labels:
    - "Object A": `x="150" y="270" font-size="14" text-anchor="middle"`
    - "Object B": `x="350" y="270" font-size="14" text-anchor="middle"`
    - "Temp: [value]°C": Within each object's indicator bar.
    - "Thermometer": `x="240" y="130" font-size="14" text-anchor="middle"`

# Interactive Controls
Slider 1: Initial Temperature of Object A (min: 0, max: 100, default: 80, step: 1)
  - Controls: The fill color of Object A's temperature indicator bar, the text value displayed for Object A's temperature, and the initial value of `tempA`.
  - Visual effect: As the slider moves, the red indicator bar changes length and color saturation to reflect the temperature, and the displayed text updates.

Slider 2: Initial Temperature of Object B (min: 0, max: 100, default: 20, step: 1)
  - Controls: The fill color of Object B's temperature indicator bar, the text value displayed for Object B's temperature, and the initial value of `tempB`.
  - Visual effect: As the slider moves, the blue indicator bar changes length and color saturation to reflect the temperature, and the displayed text updates.

Draggable Element: Thermometer Mercury Line
  - Location: Within the thermometer shape (`x="240" y="150" width="20" height="100"`). The mercury line is a rectangle inside this.
  - Drag constraint: Vertical movement only, within the bounds of the thermometer shape (y from 150 to 250).
  - Visual effect: When dragged, the mercury line's position updates, and the displayed temperature on the thermometer label changes accordingly. This acts as a direct reading tool.

# State Variables
- `tempA`: number - Current temperature of Object A (initialized by Slider 1).
- `tempB`: number - Current temperature of Object B (initialized by Slider 2).
- `heatFlowRate`: number - Magnitude of heat transfer per unit time. This will be dynamically calculated.
- `equilibriumReached`: boolean - Flag indicating if thermal equilibrium has been achieved.
- `selectedObject`: string - Tracks which object's temperature is currently displayed on the thermometer ("A" or "B").

# Update Logic
When Slider 1 changes:
  1. `tempA` is set to the slider's new value.
  2. If `selectedObject` is "A", the thermometer mercury line and label update to reflect `tempA`.
  3. Object A's temperature indicator bar is redrawn based on the new `tempA`.
  
When Slider 2 changes:
  1. `tempB` is set to the slider's new value.
  2. If `selectedObject` is "B", the thermometer mercury line and label update to reflect `tempB`.
  3. Object B's temperature indicator bar is redrawn based on the new `tempB`.
  
When draggable moves:
  1. The `y` coordinate of the mercury line is updated.
  2. `selectedObject` is set to "A" if the mercury line is within the "A" part of the thermometer, or "B" if within the "B" part (e.g., top half vs. bottom half).
  3. The displayed temperature on the thermometer label is calculated based on the mercury line's `y` position and the overall temperature range. This temperature is temporarily displayed without changing `tempA` or `tempB`.

When `tempA` and `tempB` differ and `equilibriumReached` is false:
  1. Calculate `heatFlowRate` as a function of `(tempA - tempB)`. A simple linear relationship: `heatFlowRate = k * (tempA - tempB)`, where `k` is a constant (e.g., 0.5).
  2. Calculate the change in temperature for each object: `deltaT = heatFlowRate * timeStep` (where `timeStep` is a small interval, e.g., 0.1 seconds).
  3. Update temperatures: `tempA -= deltaT`, `tempB += deltaT`.
  4. Check for thermal equilibrium: If `abs(tempA - tempB) < epsilon` (a small threshold, e.g., 0.1), set `equilibriumReached = true`.
  5. Adjust the number and opacity of heat flow arrows based on `heatFlowRate`. More arrows and brighter orange for larger differences.
  6. Update the temperature indicator bars and labels for both objects.
  7. If `selectedObject` is "A" or "B", update the thermometer to reflect the current `tempA` or `tempB` respectively.

# Educational Content
- Key concept 1: **Heat Flow Direction**: Heat is a form of energy that naturally moves from a region of higher temperature to a region of lower temperature. This simulation visually demonstrates this principle by showing orange arrows flowing from the hotter object to the colder object.
- Key concept 2: **Thermal Equilibrium**: When two objects in thermal contact reach the same temperature, there is no net flow of heat between them. The simulation shows this as the arrows disappear and the temperatures stabilize when they become equal.
- Formula display: `Heat Flow Rate ∝ (T_hot - T_cold)` or `dT/dt = -k(T_A - T_B)` (for continuous simulation). The simulation will display `Temperature of A: [tempA]°C` and `Temperature of B: [tempB]°C`.

# Quiz Questions (2-3)
1. Q: If Object A is at 70°C and Object B is at 30°C, in which direction will heat flow?
   A: From Object A to Object B.
   Wrong options: From Object B to Object A, Heat will not flow, Heat will flow both ways.
   Explanation: Heat always flows from a hotter object to a colder object.

2. Q: What happens to the temperature of Object A (initially 80°C) and Object B (initially 20°C) over time in this simulation?
   A: Object A's temperature decreases, and Object B's temperature increases until they reach the same temperature.
   Wrong options: Object A's temperature increases, Object B's temperature decreases, Both temperatures remain constant, Object A's temperature increases and Object B's decreases.
   Explanation: Heat flows from A to B, warming B and cooling A until they are at the same temperature (thermal equilibrium).

3. Q: In this simulation, what does the orange arrow intensity represent?
   A: The rate at which heat is flowing.
   Wrong options: The total amount of heat transferred, The difference in volume between the objects, The final temperature of the objects.
   Explanation: A stronger arrow indicates a faster rate of heat transfer due to a larger temperature difference.