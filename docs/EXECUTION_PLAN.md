# Execution Plan - Fuzzy Smart Home (IoT + CI)

Plan re-dated **Mon 16 Nov 2026** (started from zero). The code, graphs, tests and docs already exist, so your
three days go into **running it, understanding it, making it yours, and presenting it**.
Shift the dates to match your professor's schedule and any submission deadline.

*File locations: every document (`README.md`, `PRD.md`, `memory.md` and this plan) lives in
`docs/`. Code, `requirements.txt` and `outputs/` are in the project root. Run all commands
from the project root.*

| Day | Date | Hours | Daily goal (one sentence) |
|---|---|---|---|
| 1 | Mon 16 Nov (tonight) | ~3 h | Project runs on YOUR laptop, offline and live, and a safe copy is on GitHub |
| 2 | Tue 17 Nov | ~5 h | You understand every file, have made it yours, and have a backup demo video |
| 3 | Wed 18 Nov | ~5 h | Report is written, demo is rehearsed, and the professor has seen it |
| Buffer | Thu 19 Nov | optional | Fix leftovers, or add one extension (GA tuning / light hysteresis) |

**If you fall behind, cut in this order:** (1) the PPT, (2) the extension, (3) the video.
**Never cut:** the live demo run, understanding the code, the report with the 4 graphs,
and the 5 minutes with the professor.

Keep about 1 hour a day for exam revision. The O grade also depends on internals and
the end-sem paper, and the project supports that grade; it does not replace it.

---

## DAY 1 - Mon 16 Nov (evening, ~3 h): "Make it run"

**Goal:** see every output on your own screen and have a backup copy online.

### 1.1 Set up (20 min)
1. Unzip `smart_home_fuzzy.zip`, open the folder in Antigravity (or any editor).
2. Open a terminal inside the folder. Check Python: `python --version` (need 3.9 or newer).
   If `python` is not found, use `python3` (Mac/Linux) or `py` (Windows) everywhere below.
3. Optional but clean: `python -m venv venv`, then activate it
   (Windows: `venv\Scripts\activate`, Mac/Linux: `source venv/bin/activate`).
4. `pip install -r requirements.txt`

### 1.2 Offline run (15 min) - the part that always works
1. `python test_controller.py`  -> must end with **7 tests passed**.
2. `python run_offline.py`  -> prints a comparison table and fills the `outputs/` folder.
3. Open the four PNGs in `outputs/`: `membership_functions`, `control_surface`,
   `day_simulation`, `comparison`.

### 1.3 Read your own graphs (30 min)
Make a notes file `my_notes.md` and write ONE sentence in your own words for each graph:
- What does each coloured curve in `membership_functions.png` mean?
- In `day_simulation.png`, why does the blue line change smoothly and the orange one jump?
- In `comparison.png`, which bars favour fuzzy and which favour if-else? (Lights favour
  if-else. Notice this and be ready to say why.)

### 1.4 Live MQTT demo (60 min) - the untested part, so do it today
1. **Edit `config.py` once**: change the default `ROOT` string to something unique, for
   example `iot_ci_fuzzy_<yourname>_2026/livingroom`. Editing the file is safer than
   environment variables, because env vars must be repeated in every terminal.
2. Open **three terminals** in the project folder (activate the venv in each):
   - Terminal 1: `python controller.py` -> expect `[controller] connected, listening on ...`
   - Terminal 2: `python dashboard.py` -> a window with 7 empty graphs opens
   - Terminal 3: `python sensors.py --delay 0.2` -> prints a line every 0.2 s
3. Expected: Terminal 1 prints lines like
   `10:15  T=31.2 H=54 L=649 occ=0  ->  fan 0.0%  ac 22.0%  light 0.0%`, and the
   dashboard graphs draw themselves. A full day takes about 1 minute.
4. Stop all with `Ctrl+C`.

**If something fails:**

| Symptom | Likely cause and fix |
|---|---|
| `python` / `pip` not found | Use `python3`/`pip3` or `py -m pip` |
| `externally-managed-environment` error | Use the venv from step 1.1.3 |
| Connection timed out / refused | College Wi-Fi may block port 1883. Use your phone hotspot, or install Mosquitto and set `BROKER = "localhost"` in `config.py` (Windows: installer from mosquitto.org; Ubuntu: `sudo apt install mosquitto`; Mac: `brew install mosquitto`) |
| Controller prints nothing | Start the controller BEFORE the sensors; check all three terminals use the same `config.py`; check your internet |
| Dashboard window does not open | Linux: `sudo apt install python3-tk`. Else tell me the exact error |
| Any traceback you cannot fix | Copy the full error text and paste it to me (or to Antigravity with `memory.md` loaded) |

### 1.5 Safe copy on GitHub (20 min)
1. Create a `.gitignore` file containing two lines: `__pycache__/` and `venv/`
2. In the folder: `git init`, `git add .`, `git commit -m "Fuzzy smart home: initial version"`
3. Create an empty repo on github.com (name it `fuzzy-smart-home-mqtt`), then:
   `git remote add origin <your-repo-url>`, `git branch -M main`, `git push -u origin main`

### 1.6 Book the professor (10 min)
Send or say this (edit freely): *"Good evening sir, I have built a mini project that
connects both your subjects: a fuzzy-logic smart-home controller that receives sensor data
over MQTT. Could I show it to you for 5 minutes this week and take your feedback on what
to add?"* Asking for feedback, not marks, is what makes it land well.

### Day 1 done-check
- [ ] 7 tests pass on your laptop
- [ ] 4 graphs generated and you wrote one sentence about each
- [ ] Live demo ran at least once (or you know exactly which error blocks it)
- [ ] Code is on GitHub
- [ ] Meeting with the professor requested

---

## DAY 2 - Tue 17 Nov (~5 h): "Own it"

**Goal:** you can explain every file without looking, the project has your own
fingerprints on it, and you have a backup recording.

### 2.1 Code walkthrough (2 h) - do this in the order below
Read each file slowly, run small experiments, and be able to say the sentences given.

1. **`fuzzy_system.py` (60 min)**
   - `trapmf`: "Trapezoid shape. A triangle is a trapezoid with b = c. Shoulders use a = b or c = d."
   - `FuzzyVar.fuzzify`: "Turns a crisp number into a degree for every term."
   - `MamdaniController.infer`: walk the five steps line by line: min (AND), clip (implication),
     max (aggregation), centroid (defuzzification), deadband.
   - Rule lists: read all 26 rules once. Notice the list shorthand (`PEOPLE`) means OR.
   - **Do this worked example by hand and then check it with the code.** Inputs:
     temperature 32 degC, humidity 70 %, 4 people.
     - Fuzzify: temp warm = 0.29, hot = 0.33; humidity humid = 0.75; occupancy crowded = 1.0
     - Two fan rules fire: `crowded AND hot -> high` (strength min(1, 0.33) = 0.33) and
       `crowded AND warm AND humid -> high` (min(1, 0.29, 0.75) = 0.29)
     - Both clip the "high" shape; the centroid of the clipped shape = **86.9 %** fan.
       The if-else baseline would say 100 %.
     - Verify: `python -c "import fuzzy_system as fs; v,f=fs.fan_controller.infer(temp=32,hum=70,occ=4); print(v); [print(round(s,2),c,o) for s,c,o in f]"`
2. **`controller.py` (25 min)** - "`SmartHomeController` holds the latest readings and decides
   only when occupancy arrives with all four sensors seen. MQTT wiring is separate, so it is
   testable without a broker."
3. **`sensors.py` + `config.py` (15 min)** - "Publishes JSON to topics; occupancy goes last
   so the controller knows the cycle is complete."
4. **`simulation.py` (10 min)** - "A sine-based day with random drift and a family
   occupancy routine; seed 42 makes it repeatable."
5. **`test_controller.py` (10 min)** - read what each of the 7 tests proves.

**Questions to answer in `my_notes.md` (tricky ones the professor may ask):**
- What happens if one sensor message is lost? (Controller reuses the last value; if the
  occupancy message is lost, that cycle makes no decision.)
- Why is occupancy sent last?
- Why can the output never reach exactly 100 %? (Centroid of the "high" shape is about 90 %.)
- What is the deadband for? (Centroid of "off" alone is about 6.7 %; below 8 % we show 0.)
- Why does the fuzzy AC run when the room is empty? (Pre-cooling rule, a design choice.)
- Why do the fuzzy lights switch more often than if-else? (Occupancy jitter, no hysteresis.)

### 2.2 Make it yours (90 min)
Do all four. Each is small and each gives you a story for the viva.
1. **Change a membership function.** In `fuzzy_system.py`, move the "hot" threshold from
   (30,36,45,45) to (28,34,45,45). Run `python run_offline.py`. Describe how the graphs and
   the energy numbers changed. Then decide whether to keep it.
2. **Add one rule of your own,** for example "occupancy few AND temp hot AND humidity dry
   -> AC low instead of medium". Add a test for it in `test_controller.py`. Run the tests.
3. **Change the occupancy schedule** in `simulation.py` to your own family's real routine.
   Re-run `run_offline.py`.
4. **Update the numbers** in `README.md` (Results table), `PRD.md` section 10 and
   `memory.md` section 6 with the new output of `outputs/comparison.txt`. Docs must always
   match the code.

*Fast optional improvement (45 min, only if time remains): light hysteresis.* Keep the light
output unchanged unless the occupancy has been stable for 3 consecutive steps. This should
cut the light flicker (17 toggles vs if-else 5). Re-run and report the new toggle count.
Ask me and I will write it.

### 2.3 Backup video (45 min)
Record 60-90 seconds of the live 3-terminal demo. Windows: `Win+G`; Mac: `Cmd+Shift+5`;
or OBS. Show: controller log lines scrolling, dashboard filling, then `day_simulation.png`.
Save it as `demo.mp4`; upload to Google Drive or YouTube (unlisted) and keep the link.

### 2.4 Commit (15 min)
`git add .`, `git commit -m "Customised rules and schedule, notes, demo"`, `git push`.

### Day 2 done-check
- [ ] You can explain the five fuzzy steps without looking at the code
- [ ] You did the 32 degC / 70 % / 4 people worked example by hand
- [ ] 4 "make it yours" changes done, tests still pass, docs updated
- [ ] `demo.mp4` recorded and a link saved
- [ ] Pushed to GitHub

---

## DAY 3 - Wed 18 Nov (~5 h): "Present it"

**Goal:** a finished report, a rehearsed 3-minute demo, and the professor has seen it.

### 3.1 Report (2.5 h)
Target 6-8 pages. Outline and time (section details are in `PRD.md` section 14):

| Section | Time | Content |
|---|---|---|
| Title + abstract | 15 min | 120-150 words. Must include: "sensors and actuators are simulated; the architecture is real IoT" |
| Introduction + problem | 20 min | Threshold control problems: abrupt switching, ignores combinations, wastes energy |
| Background | 20 min | Fuzzy logic in 1 page, MQTT in 1/2 page (broker, topics, QoS) |
| Architecture | 15 min | Redraw the diagram from `PRD.md` section 5, list the MQTT topics |
| Fuzzy design | 30 min | Membership plot, rule tables, control surface |
| Implementation | 15 min | Files, simulation, controller flow |
| Results + honest discussion | 25 min | Day plot, comparison chart, table, the three caveats |
| Limitations + future work | 10 min | Simulated hardware, no comfort model, GA tuning, ESP32 |
| Conclusion + references | 10 min | References: Zadeh 1965 fuzzy sets, the MQTT specification, Mamdani 1975 |

Write the text in YOUR words; use the PRD only as a source of facts and numbers.

### 3.2 Slides (optional, 45 min)
6-8 slides: problem, architecture, fuzzy design, live demo, results, limitations + future
work, Q&A. Use the PNGs from `outputs/`.

### 3.3 Rehearsal (60 min)
1. Run the 3-minute demo script from `README.md` out loud, twice, with a timer.
2. Answer the viva questions in `PRD.md` section 16 and the six tricky questions from 2.1
   out loud. Two minutes each at most.
3. Prepare the failure plan: if the broker fails, run `python run_offline.py` and show the
   graphs, then play `demo.mp4`.

### 3.4 Meet the professor (30 min)
- Arrive with the laptop already running terminals 1 and 2, then start the sensors.
- Lead with the honest scope: "The sensors are simulated, the pipeline is real MQTT."
- Show: live dashboard -> `day_simulation.png` -> `comparison.png`.
- Mention a weakness yourself (lights flicker; the 13 % saving assumes a proportional
  AC). Volunteering this reads as maturity.
- **Close with a question:** "Sir, which CI technique would you like to see next, genetic
  algorithm tuning or a neural-network predictor?" This invites him to guide you and
  makes you memorable.
- Ask for one line of feedback you can quote in your report.

### 3.5 Final packaging (20 min)
Update the README with the demo-video link, `git push`, and save the report as PDF.

### Day 3 done-check
- [ ] Report PDF with the 4 graphs and the results table
- [ ] Demo rehearsed twice, backup plan ready
- [ ] Professor has seen it and you have his feedback written down
- [ ] GitHub repo final, with the video link in the README

---

## Staying visible in class (all week)

- **IoT class:** ask one question that links to your project, e.g. "Sir, in MQTT QoS 1,
  can the controller receive a duplicate sensor message, and does that matter?"
- **CI class:** e.g. "Sir, I saw steep output changes near the edges of the 'off' set with
  centroid defuzzification; would bisector or weighted-average be smoother?"
  (This is a real finding from your project.)
- Give a 30-second progress update when you see him. Do not wait for the final day.

## Integrity note

Check your department's rules on AI-assisted work. If it is allowed, say plainly that you
used an AI assistant to help build the project and that you then studied, tested and
changed it. Day 2 exists for exactly this: your professor will test understanding,
not the file you submit. If the project must be entirely your own work, tell your
professor before submission and use this code only as a reference.

## Buffer day - Thu 19 Nov (optional extension, pick ONE after hearing the professor)

- **Genetic algorithm tuning** of the membership-function parameters (best for a GA-heavy
  CI course; about 4-5 h with my help).
- **Light hysteresis** (about 45 min).
- **ESP32 + DHT11 + LDR** publishing real data to the same topics (if you can get hardware).

## Final checklist before submission
- [ ] `python test_controller.py` passes
- [ ] `python run_offline.py` runs from a clean clone of the GitHub repo
- [ ] Live demo works on the laptop you will carry, and on a hotspot or local broker
- [ ] README, PRD, memory.md numbers match `outputs/comparison.txt`
- [ ] Report PDF, demo video link, GitHub link ready
