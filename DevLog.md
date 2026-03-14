## 14.03.2026
Quality of Life improvements to be made:
-sending message on hitting `Enter`

Quick summary from Nettskjema (We'll do a review of the feedback in plenum)
-Design -> Sleeker design (low effort options? style libs, premade css libs etc. equiv of Tailwind? Case for switching to TypeScrip with Next.js & Tailwind? Could keep python as an API
for eventual AI side of the app)
-Fun idea: make conversations last over days i.e Chess.com functionality, having multiple conversations (extrapolated idea: chat history)
-Better definitions, some users experienced confusion, 1 ask for "dumbing down the explanation"
(overall seems to lean towards a positive sentiment)
## 08.03.2026
Quality of Life improvements to be made:
-If a 10 min timer is hit and users get disconnected it saves an emtpy chatlog
-Persistence using mongoDB for example (can just drag the json out into a jupyter notebook for data exploration admittely)
-Right now i dont see any logic making it so there's always an opposing side
-When you get paired noones obligated to write first, someone should get the "hot potato"

Bugs
-If you only have 3 topics, you get the error "No topics or tasks available"

Additions
-Added explicit conversations path override: use `python run.py --conversations-dir /disk/conversations` on Render so chat logs are persisted to disk. Running `python run.py` keeps local defaults.

Downloading files from Render using web-interface & magic wormhole:
1. open webshell in Render
2. in webshell: `\wormhole send myfile.zip` <- This returns a secret
3. in local terminal after running `pip install magic-wormhole` -> `wormhole recieve secret`