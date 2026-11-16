# Statistieken aanzetten

De game kan bijhouden hoe er gespeeld wordt. Jij bekijkt dat op
`https://89329.github.io/threejs/stats.html`. Zolang je dit niet instelt,
meet de game niets.

Wat er wordt bijgehouden:

- **bezoeken**: per bezoek apparaat (telefoon, tablet of computer), systeem,
  browser, schermgrootte, taal en de site waar iemand vandaan komt
  (bijvoorbeeld reddit.com), en hoelang de game in beeld was
- **wedstrijden**: de gekozen namen, de uitslag, de modus, het niveau, het
  stadion, hoelang de wedstrijd duurde, en of hij is uitgespeeld of gestopt
- **WK**: welk land en welk niveau, elke wedstrijd met ronde, tegenstander,
  uitslag en strafschoppen, en hoe ver ze komen

Er worden geen IP-adressen, accounts of locaties opgeslagen. Een bezoeker is
een willekeurige code in zijn eigen browser. Wie in zijn browser "niet volgen"
aan heeft staan, wordt niet geteld. Op het startscherm staat een korte regel
die zegt wat er wordt bijgehouden.

## 1. Supabase-project maken (gratis)

1. Ga naar https://supabase.com, maak een account en klik op **New project**.
   Kies een naam (bijvoorbeeld `pitch-royale`), een databasewachtwoord en een
   regio in Europa.
2. Wacht tot het project klaar is.

## 2. De tabel maken

1. Open in je project **SQL Editor**.
2. Open `stats.sql` uit deze map en zet bij `JOUW-EMAIL@voorbeeld.nl` je eigen
   e-mailadres neer.
3. Plak alles in de SQL Editor en klik op **Run**.

Daarmee mag de game alleen regels *toevoegen*, en mag alleen jouw login ze
*lezen*.

## 3. Je login maken

1. Ga naar **Authentication > Users** en klik op **Add user > Create new user**.
2. Vul hetzelfde e-mailadres in als in `stats.sql`, kies een sterk wachtwoord
   en zet **Auto Confirm User** aan.
3. Zet daarna bij **Authentication > Sign In / Providers** de optie
   **Allow new users to sign up** uit, zodat niemand anders een account kan
   maken.

## 4. De game koppelen

1. Ga naar **Project Settings > API** (of **Data API**).
2. Kopieer de **Project URL** en de **anon public** key (of **publishable**
   key).
3. Zet ze in `stats.config.js`:

   ```js
   const STATS_CONFIG = {
       url: 'https://jouwproject.supabase.co',
       key: 'de anon public key',
   };
   ```

4. Commit en push.

**Zet nooit de `service_role` of `secret` key in de game.** Die geeft volledige
toegang tot je database. De anon key mag openbaar zijn: daarmee kan iemand
alleen regels toevoegen, niet lezen of wissen.

## 5. Kijken

Open `stats.html` en log in. Vanaf dat moment telt dat apparaat niet meer mee.
Doe dit op elk apparaat waarmee je zelf speelt (laptop en telefoon), dan
tellen alleen andere mensen mee. Op de pagina kun je dat per apparaat ook weer
aan- of uitzetten.
