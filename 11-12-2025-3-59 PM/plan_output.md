# Visual Concept
The simulation will feature two distinct rectangular containers, representing objects at different temperatures. One container, on the left, will be colored a warm red, while the other, on the right, will be colored a cool blue. Small, animated dots representing heat particles will be shown within each container. Initially, the red container will have a high density of fast-moving dots, and the blue container will have a low density of slow-moving dots. A visual indicator, like a temperature gauge or number, will be displayed above each container, reflecting their current temperatures. A third, larger container in the center, initially empty or with a neutral color, will act as an intermediary or a representation of the environment. A prominent arrow will visually depict the direction of heat flow from the hotter object to the colder object.

# SVG Layout (500x350 viewBox)
- Main elements:
    - Red Rectangle (Hot Object): (x: 50, y: 100, width: 100, height: 150)
    - Blue Rectangle (Cold Object): (x: 350, y: 100, width: 100, height: 150)
    - Neutral Rectangle (Environment): (x: 175, y: 100, width: 150, height: 150)
    - Heat Particle Dots: Numerous small circles (radius: 3) scattered within the rectangles.
    - Temperature Gauge 1 (Hot): (x: 75, y: 50, width: 50, height: 10)
    - Temperature Gauge 2 (Cold): (x: 375, y: 50, width: 50, height: 10)
    - Heat Flow Arrow: (x: 225, y: 175, width: 50, height: 50) - will dynamically change position and direction.
- Color scheme:
    - Hot Object: Shades of red/orange.
    - Cold Object: Shades of blue/cyan.
    - Neutral Object: Grey or light white.
    - Heat Particles: Color-coded based on object temperature (reddish for hot, bluish for cold).
    - Arrow: Dark grey with a red tip.
- Labels:
    - Temperature Value 1: Text display above Temperature Gauge 1 (e.g., "100°C").
    - Temperature Value 2: Text display above Temperature Gauge 2 (e.g., "20°C").
    - "Hot Object" label below red rectangle.
    - "Cold Object" label below blue rectangle.
    - "Heat Flow" label near the arrow.

# Interactive Controls
Slider 1: Hot Object Temperature (min: 20, max: 100, default: 100, step: 1)
  - Controls: The temperature value displayed for the hot object and the initial speed/density of heat particles within it.
  - Visual effect: As the slider increases, the temperature value rises, the color of the red rectangle becomes more intense, and the heat particles move faster and increase in number. As it decreases, the opposite occurs.

Slider 2: Cold Object Temperature (min: 0, max: 80, default: 20, step: 1)
  - Controls: The temperature value displayed for the cold object and the initial speed/density of heat particles within it.
  - Visual effect: As the slider increases, the temperature value rises, the color of the blue rectangle becomes less intense (warmer), and the heat particles move faster and increase in number. As it decreases, the opposite occurs.

Draggable Element: "Object Separator"
  - Location: A vertical line visually separating the Red and Blue objects, adjustable to change the "distance" between them. (e.g., positioned between x=200 and x=300).
  - Drag constraint: Can be dragged horizontally between approximately x=200 and x=300, influencing the perceived rate of heat transfer.
  - Visual effect: When dragged, the position of the Heat Flow Arrow might adjust, and the speed at which particles move between objects could be subtly influenced (though the primary driver is temperature difference).

# State Variables
- `hotTemp`: number - The current temperature of the hot object.
- `coldTemp`: number - The current temperature of the cold object.
- `heatFlowRate`: number - The calculated rate at which heat is transferred.
- `particleSpeedHot`: number - Animation speed of particles in the hot object.
- `particleSpeedCold`: number - Animation speed of particles in the cold object.
- `particleDensityHot`: number - Number of particles in the hot object.
- `particleDensityCold`: number - Number of particles in the cold object.

# Update Logic
When Slider 1 changes:
  1. `hotTemp` is updated to the slider's value.
  2. `particleSpeedHot` is calculated based on `hotTemp` (e.g., `hotTemp` / 10).
  3. `particleDensityHot` is calculated based on `hotTemp` (e.g., `hotTemp` / 5).
  4. The displayed temperature value for the hot object is updated.
  5. Heat particles in the hot object animate with `particleSpeedHot` and are displayed with `particleDensityHot`.
  6. `heatFlowRate` is recalculated based on the new `hotTemp` and `coldTemp`.
  7. The Heat Flow Arrow updates its position/visibility if `hotTemp > coldTemp`.
  
When Slider 2 changes:
  1. `coldTemp` is updated to the slider's value.
  2. `particleSpeedCold` is calculated based on `coldTemp` (e.g., `coldTemp` / 5).
  3. `particleDensityCold` is calculated based on `coldTemp` (e.g., `coldTemp` / 5).
  4. The displayed temperature value for the cold object is updated.
  5. Heat particles in the cold object animate with `particleSpeedCold` and are displayed with `particleDensityCold`.
  6. `heatFlowRate` is recalculated based on the new `hotTemp` and `coldTemp`.
  7. The Heat Flow Arrow updates its position/visibility if `hotTemp > coldTemp`.
  
When draggable moves:
  1. The horizontal position of the "Object Separator" is updated.
  2. `heatFlowRate` is adjusted slightly to simulate distance (e.g., `heatFlowRate = (hotTemp - coldTemp) * (1 - (separatorPosition - 200) / 100)`), making it slower when further apart.
  3. The position of the Heat Flow Arrow is updated to span the gap between objects.

# Educational Content
- Key concept 1: **Heat is Energy in Motion:** Heat is a form of energy that flows from a region of higher temperature to a region of lower temperature. This simulation visually represents this by showing faster, more numerous particles (representing higher kinetic energy) in the hotter object, and these particles transfer their energy to the colder object.
- Key concept 2: **Temperature Difference Drives Heat Flow:** The greater the difference between the temperatures of two objects, the faster the heat will flow between them. The simulation demonstrates this by increasing the speed of the heat flow arrow and the rate of particle transfer as the temperature difference increases.
- Formula display: **Q = mcΔT** (While this is for heat quantity, we can adapt to show the principle of temperature difference driving flow). A simplified representation: **Heat Flow Rate ∝ (T_hot - T_cold)**. This will be displayed with live values from the sliders.

# Quiz Questions (2-3)
1. Q: If the red object is at 80°C and the blue object is at 30°C, in which direction will heat flow?
   A: From the red object to the blue object.
   Wrong options: From the blue object to the red object., Heat will not flow., Heat will flow equally in both directions.
   Explanation: Heat always flows from a region of higher temperature to a region of lower temperature.

2. Q: What happens to the particles in the hotter object as its temperature increases (and heat flows out)?
   A: They move faster and their kinetic energy increases.
   Wrong options: They slow down and their kinetic energy decreases., They stop moving., They become more numerous but move slower.
   Explanation: Temperature is a measure of the average kinetic energy of the particles. Higher temperature means faster particle movement and greater kinetic energy.

3. Q: If you increase the temperature of the cold object to match the hot object (e.g., both at 70°C), what will happen to the heat flow?
   A: Heat flow will stop (thermal equilibrium).
   Wrong options: Heat flow will increase., Heat flow will reverse., Heat flow will continue at the same rate.
   Explanation: Heat flows due to a temperature difference. When temperatures are equal, there is no net flow of heat, and the objects are in thermal equilibrium.