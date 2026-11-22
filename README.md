# GeoVision — site vitrine pour OVHcloud

Version autonome pour recette, sans compte client, administration ni dépendance à ChatGPT Sites. Les demandes sont envoyées par SMTP au destinataire configuré ; aucune base de données de prospects n'est créée. Le navigateur affiche un accusé de transmission seulement après acceptation par le serveur SMTP (pas une garantie de lecture).

## 1. Préparer la recette

Transférer ce dossier sur le VPS, par exemple `/home/ubuntu/geovision`, sans modifier les autres projets. Vérifier que le port local proposé 8400 est libre :

```bash
cd /home/ubuntu/geovision
sudo ss -ltnp | grep ':8400 ' || true
docker compose version
cp -n .env.example .env
chmod 600 .env
nano .env
```

Renseigner SITE_ORIGIN (origine HTTPS exacte, sans slash final), SMTP_HOST, SMTP_PORT (587 STARTTLS ou 465 TLS), SMTP_USER, SMTP_PASSWORD, MAIL_FROM (adresse autorisée par le service), MAIL_TO (adresse GeoVision confirmée). Aucun secret ne doit être ajouté à Git ni partagé dans le chat.

Le domaine de recette proposé est `rec-geovision.dsig-consulting.com`. Créer son entrée DNS si autorisé et confirmer l'adresse IP du VPS. Restreindre la recette à des IP autorisées ou un VPN via le proxy, conformément aux règles DSIG.

```bash
docker compose config --quiet
docker compose up -d --build --wait
docker compose ps
curl -fsS http://127.0.0.1:8400/healthz
```

Le healthcheck valide le serveur web, pas la délivrabilité SMTP. Le conteneur n'écoute sur le VPS que via 127.0.0.1:8400. Si le proxy Caddy est conteneurisé, cette adresse ne désigne pas le VPS : adapter au réseau edge existant avec un nom de service unique, sans ouvrir de port public.

## 2. Proxy et HTTPS

Ajouter uniquement le bloc de `Caddyfile.example` au mécanisme d'inclusion du proxy existant. Sauvegarder sa configuration, valider avec `caddy validate`, puis recharger sans arrêter les autres applications. Adapter les commandes au mode d'installation réel. Vérifier le certificat et la route avant d'autoriser des visiteurs.

## 3. Recette

```bash
python3 -m unittest -v test_server.py
```

Les tests couvrent les pages, la suppression du portail, la validation du formulaire, la protection antispam, les origines, le traitement d'une panne SMTP et le chemin SMTP simulé. En recette réelle, envoyer une demande de test via le navigateur, confirmer sa réception dans la boîte du client, vérifier Reply-To, puis tester sur mobile et ordinateur.

La version ne conserve pas les données sur disque ; la messagerie du client applique ses propres règles de conservation. L'antispam inclut un honeypot, un contrôle d'origine, une limite de taille et un plafond global de 30 demandes toutes les 10 minutes par instance. Pour exposition à fort trafic prévoir une limitation au reverse proxy et une protection antibot supplémentaire. Configurer SPF, DKIM et DMARC avec le fournisseur de messagerie.

## 4. Avant production

- Confirmer le domaine définitif (propriété du client), le destinataire, la localisation de l'hébergement et les coordonnées légales.
- Compléter et valider la page Informations & confidentialité, notamment durée de conservation, contact pour les droits, hébergeur et mentions de l'éditeur.
- Faire valider le site et le formulaire par GeoVision.
- Lever le blocage d'indexation dans robots.txt et retirer les éventuelles directives noindex après validation.
- Remplacer SITE_ORIGIN et le bloc proxy par le domaine de production, puis recréer le service et tester HTTPS + formulaire.
- Organiser des sauvegardes versionnées et externalisées des fichiers, configurations et secrets (chiffrés), les tester et configurer un contrôle de disponibilité externe.

## Rollback

Conserver l'archive de la version précédente et la configuration de proxy avant chaque changement. En cas d'échec, restaurer le dossier/version et la configuration sauvegardés, valider le proxy, reconstruire uniquement le service GeoVision puis contrôler le healthcheck. Ne jamais utiliser `docker system prune` ni arrêter les autres projets.
