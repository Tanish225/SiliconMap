# SiliconMap

SiliconMap is a VLSI placement optimizer and visualization tool I built from scratch in Python. It takes chip components (like ALUs, Caches, and Registers) and figures out the most efficient way to pack them onto a restricted silicon die. 

Instead of just snapping things to a grid, it acts like a physics engine. It tries to keep wire lengths short, prevents components from overlapping, and actively avoids creating thermal hotspots by keeping high-power components away from each other.

## How it Works

The core of the project runs on an algorithm called **Simulated Annealing**. If you aren't familiar with it, it mimics the way metal cools and crystallizes. 

When you start the optimizer, the "temperature" is high. The algorithm intentionally makes chaotic, sometimes terrible moves (throwing blocks around) so it doesn't get stuck in a bad layout early on. As the temperature slowly drops, the movements get smaller and more deliberate, eventually "freezing" the components into a highly optimized arrangement.

It evaluates every single move using a cost function that calculates four main things:
* **Wirelength:** Are connected components close to each other?
* **Overlap:** Are physical blocks crashing into one another?
* **Boundaries:** Is anything hanging off the edge of the chip?
* **Thermal Dispersion:** Are high-power components (like the ALU) sitting too close to other hot components, risking a silicon meltdown?

## Getting Started

You'll need Python 3.8 or newer installed on your machine. The only external dependency is `matplotlib`, which is used to draw the real-time analytics graphs.

### Windows Setup

Open your command prompt or PowerShell and run:

1. Clone the repo and navigate into it:
   ```cmd
  git clone [https://github.com/Tanish225/SiliconMap.git]
   cd SiliconMap

2. Set up a virtual environment:
python -m venv venv
venv\Scripts\activate

3. install matpotlib:
pip install matplotlib

4. run the app:
python -m app.main

### MacOS X Setup
Open your terminal and run:

1. Clone the repo and navigate into it:
git clone [https://github.com/Tanish225/SiliconMap.git]

2. Setup a virtual environment:
python3 -m venv venv
source venv/bin/activate

3. Install matplotlib:
pip3 install matplotlib

4. run the app:
python3 -m app.main

## Usage
When you open the app, you can start from scratch or load a pre-built layout.
To start quickly: Click "Load JSON" on the left panel and select sample_chip.json to see a mini-processor layout.
Adding blocks: Use the buttons on the left to spawn standard components.
Editing: Click on any block to select it. Once selected, you can hit your Delete key to remove it, or click Connect To... to wire it up to another block.
Optimizing: Hit "Run Optimizer". You'll see the algorithm kick in, bouncing the blocks around the canvas while the dual graphs track the cost dropping and the temperature decaying in real-time.
Smart Resizing: If you add too many components, the engine will detect that the packing density is dangerously high and ask if you want to automatically expand the chip boundaries.
Saving: Click "Save Results" to dump the final optimized coordinates into a new JSON file so you can use it later.