PC:
Zprvu je třeba tvorba venv:
Je třeba být ve složce Python_Backend.
Do terminálu: "python3 -m venv venv"

Aktivace:
Je třeba být ve složce Python_Backend
Do terminálu: ".\venv\Scripts\Activate.ps1"

pak: "cd backend"
pak: "python -m uvicorn main:app --reload"


RPI:
Pro pozorování logu:
docker logs -f drinkmaker-backend

source venv/bin/activate

-----------------------------------------------------------------------------------------------------------------
PEP8 konvence:
V Pythonu se hodně používají konvence PEP8 (oficiální stylopis).

🔹 Pojmenovávání v Pythonu
1. Moduly a soubory

vše malými písmeny, případně oddělené podtržítkem _

✅ all_states.py, glasses_state.py, system_state.py

❌ AllStates.py, SystemState.py

2. Třídy

PascalCase (každé slovo s velkým písmenem, bez podtržítek)

✅ class InputState:

✅ class GlassesState:

❌ class input_state:

❌ class inputstate:

3. Proměnné a instance objektů

malými písmeny, slova oddělovat podtržítkem _

✅ input_state = InputState()

✅ glasses_state = GlassesState()

❌ Input_State = InputState()

👉 Velká písmena se používají jen pro konstanty, ne pro instance.

4. Konstanty

velkými písmeny, případně s podtržítkem

✅ MAX_SPEED = 150

✅ DEFAULT_TIMEOUT = 10

5. Funkce a metody

stejně jako proměnné → snake_case

✅ def update_mode_from_json(self, msg):

❌ def UpdateModeFromJson(self, msg):

6. Balíčky (adresáře)

malé písmo, pokud víceslovné → s podtržítkem

✅ services/

✅ api_endpoints/

❌ Services/
