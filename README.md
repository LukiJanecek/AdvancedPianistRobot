# AdvancedPianistRobot
PRII + OSRC + MITR

Pianista 
=> 36 bílýh kláves 
=> 25 čených kláves 



REST API backend (FastAPI) + připraveno pro React frontend

- Spuštění docker compose
docker compose up -d

- Ověř běžící kontejnery
docker ps

- Pro nový build
docker compose up -d --build


- Zastavení docker compose – jen zastaví běžící kontejnery, ale nechá je vytvořené (můžeš je znovu spustit docker compose start).
docker compose stop 

- Zastaví a smaže kontejnery, ale nesmaže image ani volumes.
docker compose down
