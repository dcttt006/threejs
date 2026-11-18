# Online spelen aanzetten

Met **Online** op het startscherm spelen twee vrienden tegen elkaar, elk op
hun eigen computer of telefoon. Je maakt een account met alleen een
gebruikersnaam en een wachtwoord, stuurt vriendschapsverzoeken en daagt een
vriend uit die online is. Zonder vriendschap kan het ook: de een maakt een
code van vier cijfers, de ander typt die in.

Het werkt op hetzelfde Supabase-project als de statistieken
(`stats.config.js`). Je hoeft dus geen nieuw project te maken. Twee dingen
moet je één keer instellen.

## 1. De tabellen maken

1. Open je project op https://supabase.com en ga naar **SQL Editor**.
2. Plak alles uit `online.sql` en klik op **Run**.

Dat maakt drie tabellen:

- **profiles**: de gebruikersnaam bij elke account
- **friendships**: vriendschapsverzoeken en vrienden
- **matches**: de uitslag van elke online wedstrijd, voor "Onderling"
  (gewonnen, gelijk, verloren) in de vriendenlijst

De regels in het bestand zorgen dat iedereen alleen zijn eigen vrienden en
uitslagen ziet.

## 2. Inloggen zonder e-mail

Supabase logt mensen in met een e-mailadres. De game maakt van een
gebruikersnaam zelf een adres dat niemand leest (`spits9@spelers.pitchroyale.nl`).
Supabase mag daar dus geen mail heen sturen:

1. Ga naar **Authentication → Sign In / Providers**.
2. Zet bovenaan **Allow new users to sign up** aan. Anders kan niemand een
   account maken.
3. Open **Email** en zet **Confirm email** uit. Klik op **Save**.

Laat **Email** zelf aan staan. De statistieken blijven veilig: alleen jouw
e-mailadres mag ze lezen (`stats.sql`), ook als anderen een account hebben.

## Hoe een wedstrijd werkt

- Wie de code maakt of uitdaagt, speelt rood (thuis) en in zijn eigen gekozen
  stadion. Zijn browser speelt de echte wedstrijd: de bal, de keepers en de
  computerteamgenoten.
- De andere speler (blauw) stuurt zijn toetsen of stick en krijgt het veld
  terug.
- De twee browsers proberen eerst rechtstreeks met elkaar te praten (WebRTC).
  Dat is het snelst. Lukt dat niet, bijvoorbeeld op sommige mobiele
  netwerken, dan loopt alles via Supabase. Dat is iets trager, maar het werkt
  wel. Bij een rechtstreekse verbinding zien de twee browsers elkaars
  IP-adres. De game slaat dat nergens op.
- Bij **Uitdagen** of **Code maken** kies je eerst wat jullie spelen:
  - **Wedstrijd**: 90 seconden.
  - **Strafschoppen, normaal**: meteen naar de stip, rood tegen blauw, in het
    stadion van wie uitdaagt.
  - **Strafschoppen WK**: in MetLife Stadium met WK-shirts en vlaggen. Jullie
    kiezen allebei een land en het land van de ander is dan niet meer te
    kiezen.

  Bij strafschoppen kiezen de schutter en de keeper tegelijk. De keeper ziet
  niet waar de schutter op richt. Na 12 seconden zonder schot volgt een zacht
  schot door het midden. Na 8 seconden zonder keuze blijft de keeper in het
  midden staan.
- Online is er geen pauze. Met de pauzeknop kun je de wedstrijd verlaten.
- Na de wedstrijd kun je om **Revanche** vragen. Als jullie allebei klikken,
  begint een nieuwe wedstrijd.

## Wat het gratis plan aankan

Supabase Realtime is gratis tot ongeveer 2 miljoen berichten per maand. Een
wedstrijd die via Supabase loopt, kost er ongeveer 2.000 tot 3.000. Met een
rechtstreekse verbinding zijn het er maar een paar.
