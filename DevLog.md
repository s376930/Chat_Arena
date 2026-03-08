## 08.03.2026
Quality of Life improvements to be made:
-If a 10 min timer is hit and users get disconnected it saves an emtpy chatlog
-Persistence using mongoDB for example (can just drag the json out into a jupyter notebook for data exploration admittely)
-Right now i dont see any logic making it so there's always an opposing side
-When you get paired noones obligated to write first, someone should get the "hot potato"

Bugs
-If you only have 3 topics, you get the error "No topics or tasks available"

Additions
-Added a mode to running the app with `python run.py --mode server` which just makes the conversations logs get saved to `disk/conversations` which is the filepath I made for a disk on Render. To run the app localy just run `python run.py` as before.