# 🚁 FlytBase — Advanced Tactical Dashboard  
### Autonomous Drone Pathfinding Simulation Using Dijkstra’s Algorithm

![Project Status](https://img.shields.io/badge/STATUS-OPERATIONAL-success?style=for-the-badge)
![Language](https://img.shields.io/badge/PYTHON-3.8%2B-blue?style=for-the-badge&logo=python)
![Engine](https://img.shields.io/badge/ENGINE-PYGAME-yellow?style=for-the-badge&logo=pygame)

---

## 📂 Mission Briefing

**FlytBase** is a high-fidelity autonomous drone pathfinding simulation designed to visualize optimal navigation in complex environments. The system computes the most cost-efficient flight path from a deployment point to a target destination while accounting for obstacles and high-resistance wind zones.

The simulation features a **Special Operations–style tactical interface**, including scanlines, real-time telemetry, animated visual effects, and an interactive grid editor.

---

## ✨ Key Features

- **⚡ Optimized Pathfinding**  
  Implements **Dijkstra’s Algorithm** using a priority queue (`heapq`) to compute the shortest-cost path in a weighted grid environment.

- **🌪️ Dynamic Terrain Weights**
  - **Clear Space:** Standard movement cost of `1`
  - **Wind Zones:** High-resistance terrain with cost `5`
  - **Obstacles:** Impassable no-fly zones excluded from traversal

- **📊 Real-Time Telemetry**
  - Simulated battery level fluctuations  
  - Signal strength variation  
  - CPU load with jitter effects

- **🖥️ Tactical User Interface**
  - Animated scanlines and radar-style sweeps  
  - Real-time event log console for system status updates

- **🖱️ Interactive Grid Environment**
  - Mouse-based terrain placement  
  - Real-time updates without restarting the simulation  
  - Immediate visual feedback during editing

---

## 🛠️ Installation and Deployment

### Prerequisites
- Python **3.8 or higher**
- `pygame` library

### Setup Instructions

1. **Clone the Repository**
   ```bash
   git clone [https://github.com/TarunSitaraman/drone-pathfinder.git](https://github.com/TarunSitaraman/drone-pathfinder.git)
   cd drone-pathfinder
   ```
2. **Install Dependencies**

```bash
pip install pygame
```

3. **Launch Mission**
```bash
python drone_router.py
```

--- 

## 🎮 Operator Controls

The dashboard is controlled via keyboard shortcuts and mouse interaction.

| Key / Input | Action | Description |
| :--- | :--- | :--- |
| **`Left Click`** | **Draw** | Place the currently selected element (Wall, Wind, etc.) on the grid. |
| **`Right Click`** | **Erase** | Remove elements from the grid. |
| **`1`** | **Obstacles** | Select the **Wall** tool (No-fly zone). |
| **`2`** | **Wind Zone** | Select the **Wind** tool (High travel cost). |
| **`3`** | **Relocate Drone** | Move the Start Point. |
| **`4`** | **Relocate Target** | Move the End Point. |
| **`SPACE`** | **EXECUTE** | Run the pathfinding algorithm. |
| **`R`** | **RESET** | Clear the grid and reset system status. |
