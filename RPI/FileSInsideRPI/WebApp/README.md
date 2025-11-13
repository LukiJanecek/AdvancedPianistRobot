# AdvancedPianistRobot
PRII + OSRC + MITR

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



docker compose logs

docker compose logs backend


docker compose logs -f

docker compose logs -f backend


docker ps

docker logs -f <container_name>

