# HRI_RA_project
Project for the **H**uman **R**obot **I**nteraction and **R**easoning **A**gents modules belonging to the *Elective in AI* course at Sapienza University.

<img src="https://i.imgur.com/FDRb0dM.png"  width="300" height="60">

>**EnviroMate** is a social robot which aims to raise awareness among students about recycling. It can interact both with primary school students and secondary school students. With the former it can play a *game* with an educational purpose, and with the latter, it can inform them by showing some *news* from the web about the argument. For students of all types the robot can also, if requested, show the way to dispose of waste into the correct bin (plastic, paper, waste and organic waste) when the item is exhibited by the user.

![demo](https://github.com/lavallone/EnviroMate/raw/main/assets/demo.gif)

* **docker** folder contains the scripts to *build* and *run* the ***pepper-hri*** image.
  ```
  cd docker/
  ./build.bash
  ./run.bash
  docker exec -it pepperhri tmux a
  ```
* **src** folder is a copy of what it's contained in our local machines in "*/home/user_name/src*" (***modim*** and ***pepper\_tools*** ).
    * *modim* is needed for the interaction. We have practically only modified the ***interaction_manager.py*** file in *src/modim/src/GUI* folder for being able to use additional functionalities.
    * *pepper\_tools* capabilities were instead leveraged (and in some cases modified) for executing robot gestures and simulating voice, proximity and potential touches of the users.
* Finally **pepper_interaction** is the main folder in which we developed all the code to make the interaction happens.
  * We changed *html* and *javascript* files (*index.html* and *qaws.js*) to have a graphical interface to our liking.
  * In *scripts* folder we have the two files which constitute the backbone of our human-robot interaction project: *(i)* ***main\_behaviour.py*** is responsible of the overall robot behaviour pipeline; *(ii)* ***human_interaction_fake.py*** executes all simulated actions which a human can perform during an interaction.

## Set up ⚙
* Create a *python conda environment* to be able to run (outside the ***pepper-hri*** docker container), two *services* developed by us: the **garbage detector** based on YOLOv5 and the **shortest path** planner to indicate the nearest bin where to throw waste items (Planning and Knowledge Reasoning involved). The latter consists of 3 different strategies (a classical PDDL planner, a Q-learning RL algorithm and a reward shaping method based on $LTL_f$ goal specifications). These two *services* are provided through *sockets* mechanism.
  ```
  ## run this command in the following folders (within the created conda environment): 
  # pepper_interaction/RA/planning
  # pepper_interaction/RA/KR_RL
  # pepper_interaction/vision/garbage_detection
  # pepper_interaction/vision/garbage_detection/yolov5
  pip install -r requirements.txt
  ```
  Run to set up the socket servers:
  ```
  python pepper_interaction/vision/garbage_detection/GarbageDet_detect.py
  ```
  ```
  python pepper_interaction/RA/shortest_path.py
  ```
* In the *docker* container we first need to run the **modim server**:
  ```
  python ws_server.py -robotport <ROBOT_PORT_NUMBER>
  ```
  Then the script to simulate users behaviours:
  ```
  python human_interaction_fake.py -robotport <ROBOT_PORT_NUMBER>
  ```
  Finally the python code to run the actual interaction with Pepper robot:
  ```
  python main_behaviour.py
  ```
