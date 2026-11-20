# OBS Screen Translator

Živý preklad textu z obrazu pre streamerov. Program číta text v zdroji [OBS Studio](https://obsproject.com/) (hra zo
zachytávacej karty, zachytenie hry, okno), preloží ho jazykovým modelom, ktorý beží vo vašom počítači, a preklad nakreslí
cez pôvodný text alebo tam, kam chcete. Diváci vidia titulky, správy, pokyny, čety v telefóne a menu vo svojom jazyku;
z počítača nič neodchádza.

- **Číta, čo si vyberiete**: celý obraz alebo oblasti, ktoré nakreslíte. Preklad oblasti sa môže ukázať na inom mieste
  a vo vlastnom zdroji OBS, ktorý v OBS umiestnite, orežete a skryjete ako každý iný zdroj.
- **Pokojný obraz**: naklonený text, napríklad telefón v ruke, sa preloží v jeho uhle; preklad nasleduje malé pohyby
  svojho textu bez blikania a na statickom obraze stojí.
- **Vlastný vzhľad**: písmo, veľkosť, farby, hranaté pozadie a mäkký tieň okolo písma, pre všetky oblasti alebo každú
  zvlášť, so vzorkou v OBS počas úprav.
- **Nastaví sa sám**: so súhlasom zapne server WebSocket v OBS, nainštaluje Ollamu a stiahne model TranslateGemma (4b,
  12b alebo 27b). Kláves zobraziť/skryť funguje z ktoréhokoľvek okna aj zo Stream Decku.
- **Po slovensky aj po anglicky**, s návodom v programe; v zoznamoch je 164 jazykov.

Inštalátor stiahnete z [Releases](https://github.com/Sl0vakistan/obs-screen-translator/releases/latest).

English version: [README.md](README.md)

Otvorený zdrojový kód pod licenciou MIT, pozri [LICENSE](LICENSE).

## Vibe coding, priznane

Nápad, skúšanie na skutočnom streame a všetky rozhodnutia sú od streamera, ktorý nie je programátor a ani sa naňho nehrá.
Celý kód, inštalátor aj túto dokumentáciu napísal AI asistent na programovanie (Claude od Anthropicu) v rozhovore s ním.
Kód nikto neprešiel riadok po riadku. Berte ho tak: prečítajte si ho, kým sa naň spoľahnete, a nahláste, čo sa pokazí.

## Inštalácia

1. Nainštalujte [OBS Studio](https://obsproject.com/) a raz ho spustite.
2. Zo stránky Releases tohto repozitára stiahnite `OBS-Screen-Translator-Setup-<verzia>.exe` a spustite ho. Inštaluje sa
   pre aktuálneho používateľa, bez práv správcu.

Zvyšok si program nastaví sám pri prvom spustení, pri každom kroku sa najprv spýta:

- Ak je server WebSocket v OBS vypnutý, program ponúkne, že ho zapne. OBS číta toto nastavenie len pri štarte, takže ho
  treba na chvíľu zavrieť; program na to počká, nastavenie zmení a pôvodné nechá v súbore
  `config.before-screen-translator.json` v tej istej zložke.
- Ak chýba [Ollama](https://ollama.com/), v ktorej beží prekladový model, program ponúkne, že ju stiahne z ollama.com
  (1,9 GB) a nainštaluje. Stiahnutý inštalátor spustí len vtedy, keď má podpis Ollamy. Ollama po inštalácii otvorí
  vlastné okno s príkazmi do terminálu; prekladač ich nepotrebuje, pozri [Ollama](#ollama).
- Prekladový model (8,1 GB) sa stiahne raz.

Prvé dve veci môžete spraviť aj ručne: v OBS *Nástroje > Nastavenia servera WebSocket > Povoliť server WebSocket*
a inštalátor z [ollama.com/download](https://ollama.com/download).

Inštalátor nie je podpísaný, takže Windows SmartScreen môže upozorniť na neznámeho vydavateľa; pokračuje sa cez *Ďalšie
informácie > Spustiť aj tak*. Ak nepodpísaný inštalátor spúšťať nechcete, spustite program zo zdrojového kódu (nižšie).

## Použitie

1. Spustite OBS a *OBS Screen Translator* z ponuky Štart, v ľubovoľnom poradí. Program na OBS počká.
2. Skontrolujte jazyky v **Prekladať z** a **Prekladať do** v časti *Preklad*. Cieľový jazyk je na začiatku jazyk vášho
   Windows. **Model** vyberá medzi TranslateGemma 4b (slabšie preklady, asi 2,7 GB pamäte grafiky), 12b (odporúčaný,
   asi 7,5 GB) a 27b (najlepšie preklady, asi 17 GB); riadok pod ním ukazuje grafickú kartu vášho počítača a jej pamäť.
   Model väčší než karta beží sčasti na procesore a prekladá oveľa pomalšie; okno na to upozorní.
3. Skontrolujte **Zdroj v OBS** v časti *Hra*. Ak je v scéne, ktorá ide do vysielania, práve jedna zachytávacia karta,
   vyberie sa sama; rovnako jediné zachytenie hry, okna alebo obrazovky. Inak vyberte hru zo zoznamu. *Obnoviť* načíta
   zoznam zdrojov z OBS znova.
4. Voliteľne **Oblasti na čítanie**. *Vybrať...* ukáže aktuálny obraz hry; myšou potiahnite obdĺžnik okolo každej časti,
   ktorú chcete prekladať, napríklad okolo titulkov a telefónu. Obdĺžnikov môže byť viac. Text mimo nich sa ignoruje.
   *Odobrať poslednú* a *Odobrať všetky* obdĺžniky odoberú; bez obdĺžnika sa číta celý obraz. Preklad sa kreslí cez
   pôvodný text, ak mu nedáte iné miesto: zvoľte *Kresliť, kde sa oblasť [číslo] ukáže* a potiahnite miesto (modré, so
   šípkou od oblasti). Miesto drží pomer strán svojej oblasti, takže preklad sa tam presunie a zväčší či zmenší bez
   zdeformovania. *Ukázať tam, kde sa číta* to vráti. *OK* výber potvrdí;
   *Použiť* oblasti uloží bez zavretia okna a zmeny sa hneď ukážu v OBS. Kým je okno otvorené, každá oblasť ukazuje v OBS
   svoje číslo tam, kde sa objavia jej preklady.
5. Voliteľne **Vzhľad** → *Upraviť...* otvorí *Vzhľad prekladov*: písmo, veľkosť (ako pôvodný text alebo pevná), tučné,
   kurzíva, farba textu, farba a krytie pozadia, hranaté pozadie (0 žiadne, plynulo rastie, pri 8 zakryje pôvodný text),
   tieň okolo písma (mäkký tieň bez hrán, od žiadneho po veľký, s vlastnou intenzitou), obrys a zarovnanie. *Nastavenie pre* určuje, či meníte predvolený
   vzhľad, ktorý používajú všetky oblasti, alebo vzhľad jednej oblasti; oblasť môže ostať pri predvolenom vzhľade alebo
   dostať vlastný. Zmeny platia hneď a kým je editor otvorený, OBS ukazuje vzorový preklad s upravovaným vzhľadom.
   **Ukazuje sa v zdroji OBS** pošle preklady oblasti do iného zdroja prehliadača: *Nový zdroj...* ho pridá do OBS,
   *Odstrániť zdroj* ho z OBS zas odstráni a jeho oblasti vráti do prvého zdroja. Každý zdroj sa dá v OBS samostatne
   umiestniť, orezať, dať mu filtre a zobraziť či skryť, napríklad titulky vo všetkých scénach a telefón len v niektorých.
6. Voliteľne **Kláves zobraziť/skryť**. Stlačte *Nastaviť...* a potom funkčný kláves (F1 až F24) alebo kombináciu s Ctrl
   či Alt. Ten kláves preklady zobrazí a skryje, nech je v popredí ktorékoľvek okno, aj keď ho pošle Stream Deck.
7. Stlačte **Spustiť**. Keď zapnete **Spustiť preklad hneď po otvorení programu**, nabudúce to program spraví za vás.

Tlačidlo vedľa **Pomocníka** prepína program medzi slovenčinou a angličtinou; kým si nevyberiete, riadi sa jazykom
Windows. Každé okno sa dá zväčšiť aj zmenšiť; v *Oblastiach na čítanie* sa obraz prispôsobí oknu a drží pomer strán
zdroja v OBS.

Pri prvom spustení program do scény, ktorá práve ide do vysielania, pridá zdroj prehliadača *Translation overlay*.
Zdroje pridané cez *Nový zdroj...* vzniknú rovnako, keď sa preklad spustí alebo reštartuje.

V ponuke **Pomocník** vpravo hore je krátky návod (*Inštalácia a nastavenie*), zmeny nainštalovanej verzie (*Novinky vo
verzii <verzia>*), *Podrobnosti* s verziou, licenciou a miestom nastavení a uložených prekladov, *Otvoriť priečinok
s nastaveniami* a *Stránka projektu*. Okno vypisuje každý preložený text a čas, ktorý to trvalo.

Jazyk alebo model zmeníte výberom iného v okne. Preklad sa spustí znova sám, netreba ho predtým zastavovať. Každý jazyk
aj model má vlastné uložené preklady. Model, ktorý na počítači ešte nie je, sa najprv stiahne a doterajší sa uvoľní
z grafickej karty. Rovnako sa počas prekladu dajú zmeniť oblasti.

Menšie oblasti znamenajú menej čítania a menej prekladania a žiadne preklady cez časti obrazu, ktoré vás nezaujímajú.
Najviac pomôžu na obrazovkách plných textu; pozri *Namerané*.

Oblasť sa číta, len kým je zdroj, ktorý ukazuje jej preklady, viditeľný v scéne, ktorá ide do vysielania. Keď zdroj
skryjete, jeho oblasti sa nečítajú ani neprekladajú; keď sú skryté všetky zdroje prekladu, program čaká, kým niektorý
zobrazíte. Klávesa z okna programu zobrazí a skryje všetky zdroje prekladu naraz, vo všetkých scénach, kde sú. Zdroj
prekladu musí byť priamo v scéne, nie vo vnorenej scéne.

Zavretím okna preklady z obrazu zmiznú a prekladový model sa hneď uvoľní z grafickej karty. Kým program beží, Ollama
drží model načítaný aj medzi prekladmi.

## Ollama

[Ollama](https://ollama.com/) je bezplatný program, v ktorom na vašom počítači beží prekladový model. Prekladač jej posiela
text na preklad; nič neodchádza z počítača.

- Ollamu netreba spúšťať a do terminálu netreba nič písať. Po stlačení **Spustiť** ju program spustí na pozadí, ak
  nebeží, a stiahne model, ak chýba (8,1 GB; okno ukazuje percentá). Keď môže prekladať, napíše *prekladový model je
  pripravený*.
- Po inštalácii Ollama otvorí vlastné okno *Launch* s vetou „Copy a command and run it in your terminal" a príkazmi ako
  `ollama launch claude`. Tie spúšťajú AI nástroje na programovanie a s prekladačom nesúvisia: okno zavrite, Ollama beží
  ďalej na pozadí.
- Ručná inštalácia: spustite `OllamaSetup.exe` z [ollama.com/download](https://ollama.com/download). Inštaluje sa pre
  aktuálneho používateľa, bez práv správcu, a nepotrebuje účet.
- Beží? Adresa <http://127.0.0.1:11434> v prehliadači ukáže *Ollama is running*. `ollama list` v príkazovom riadku vypíše
  stiahnuté modely.
- Model sa dá stiahnuť pred streamom: raz stlačte **Spustiť** a počkajte na *prekladový model je pripravený*, alebo
  v príkazovom riadku spustite `ollama pull translategemma:12b`.
- Pri menej než asi 8 GB voľnej pamäte grafiky vyberte v *Preklad* → *Model* TranslateGemma 4b (3,3 GB, asi 2,7 GB
  pamäte grafiky). Prekladá citeľne horšie a stiahne sa pri ďalšom stlačení **Spustiť**.
- Ollama drží modely v `%USERPROFILE%\.ollama\models`. Inam ich presmeruje *Model location* v nastaveniach Ollamy (Ollamu
  otvorte z ponuky Štart) alebo premenná prostredia `OLLAMA_MODELS`, najlepšie ešte pred stiahnutím modelu.
- Ollama na inom počítači: tam v nastaveniach Ollamy zapnite *Expose Ollama to the network* (alebo nastavte
  `OLLAMA_HOST=0.0.0.0`) a povoľte ju vo firewalle Windows; tu nastavte v `settings.json` (*Pomocník* → *Otvoriť
  priečinok s nastaveniami*) `ollama_url` na
  `http://<adresa toho počítača>:11434`. Každý preklad potom ide cez Ollamu a trvá asi o tretinu sekundy dlhšie, lebo
  priame spojenie s modelom funguje len na tom istom počítači.
- *Ollama sa nespustila*: spustite Ollamu z ponuky Štart, počkajte na jej ikonu pri hodinách a znova stlačte **Spustiť**.
- Prerušené sťahovanie modelu pokračuje tam, kde skončilo, keď znova stlačíte **Spustiť**.

## Ako to pracuje

1. Štyrikrát za sekundu si program cez vstavaný WebSocket server vypýta od OBS snímku zdroja s hrou.
2. [RapidOCR](https://github.com/RapidAI/RapidOCR) (modely PP-OCR) nájde a prečíta text v celej snímke. Beží na grafickej
   karte cez DirectML, ktorý funguje na každej karte s DirectX 12, alebo na procesore.
3. Riadky, ktoré patria k sebe (dvojriadkový titulok, odsek správy), sa spoja do jedného bloku. Každý riadok sa meria
   v jeho vlastnom smere, takže naklonený text, napríklad telefón v ruke, sa spojí správne a preloží v rovnakom uhle.
4. Blok preloží [TranslateGemma](https://ollama.com/library/translategemma) cez Ollamu. Vety idú po jednej hneď, ako sa
   objavia; krátke nápisy, napríklad položky menu, v dávkach do 12 kusov. Ollama pri každej požiadavke strávi asi 0,35 s
   ešte pred prácou modelu, preto program posiela text priamo llama-serveru, ktorý Ollama pre model spustila, s rovnakou
   šablónou a nastaveniami. Najprv si overí, že skúšobná veta vyjde presne ako cez Ollamu, a pri akejkoľvek chybe sa
   vráti k Ollame.
5. Zdroj prehliadača v OBS (`overlay.html`) dostane preklady cez lokálny WebSocket a každý nakreslí na miesto textu, ktorý
   nahrádza.

Do modelu ide len nový text. Text, ktorý na obraze ostáva, sa preloží raz, a každý preklad sa ukladá na disk, takže menu,
ktoré už program videl, sa ukáže hneď, aj po reštarte.

Preklad sa zobrazí, až keď sa text dvakrát po sebe prečíta takmer na tom istom mieste, takže text, ktorý cez obraz prebehne
s kamerou (nápisy a evidenčné čísla áut), ostane bez prekladu. Zobrazený preklad potom nasleduje svoj text, kým sa hýbe len
trochu, napríklad telefón v ruke, a plynulo sa presúva namiesto blikania; na statickom obraze sa nehýbe vôbec. Starý preklad ostane, kým sa nepreloží text, ktorý
ho nahradil.

## Čo treba

- Windows 10 alebo 11, 64-bitový. Program vznikol a bol skúšaný len na Windows 11.
- OBS Studio. Program vznikol a bol skúšaný s OBS 33. Nastavenia servera WebSocket číta zo súboru
  `plugin_config\obs-websocket\config.json`; verzie OBS, ktoré ich ešte držia v `global.ini`, nie sú podporované.
- Ollama; program ju vie nainštalovať. Model `translategemma:12b` potrebuje asi 7,5 GB pamäte grafiky; `translategemma:4b` asi 2,7 GB a prekladá citeľne
  horšie; `translategemma:27b` (stiahnutie 17,4 GB) asi 17 GB a kartu s viac než 16 GB pamäte. Model 27b sa neskúšal.
- Grafická karta s DirectX 12 na čítanie textu. Bez nej čítanie beží na procesore a zamestná niekoľko jadier.

## Jazyky

V zoznamoch je 164 položiek: 160 základných jazykov z tabuľky jazykov TranslateGemma, filipínčina, brazílska portugalčina
a zjednodušená a tradičná čínština. Google uvádza, že model je stavaný pre 55 jazykov, takže menej bežné budú slabšie. Na streame sa skúšala len
angličtina do slovenčiny.

Čítanie textu pozná latinku a čínštinu. Hra v inom písme (cyrilika, arabské písmo, kórejčina a ďalšie) sa zatiaľ neprečíta
správne, nech vyberiete akýkoľvek jazyk.

## Nastavenia

Jazyky, model, zdroj s hrou, oblasti na čítanie a miesto, kde sa ukazujú, vzhľad prekladov a zdroje OBS, do ktorých idú,
kláves zobraziť/skryť, automatický štart a jazyk programu sa nastavujú v okne. Všetko ostatné je v súbore `settings.json`, ktorý vznikne pri prvom spustení
v `%APPDATA%\OBS Screen Translator` (pri spustení zo zdrojového kódu vedľa `translator.py`). Zmeny platia po novom spustení
programu. Tabuľka všetkých položiek je v [README.md](README.md#settings). Najdôležitejšie:

- `context` – jedna alebo dve anglické vety, ktoré modelu povedia, aký text dostáva a ako má čitateľa oslovovať. Pri
  preklade dialógov do slovenčiny pomôže dopísať: `Dialogue is colloquial and informal: address a single person as 'ty',
  never the formal 'vy'.`
- `model` – vyberá sa v okne; sem sa dá zapísať aj iný model z Ollamy, to sa však neskúšalo. `ollama_url` môže ukazovať
  aj na iný počítač.
- `ocr_on_gpu` – `false` presunie čítanie textu na procesor.

## Spustenie zo zdrojového kódu a zostavenie

```
py -3 -m pip install -r requirements.txt
start-translator.cmd
```

`start-translator.cmd --preview` prečíta jednu snímku z OBS, vypíše nájdené texty s prekladom a uloží `preview.png`
s vyznačenými textami. `build.ps1` zostaví program do `dist\OBS Screen Translator` a, ak je nainštalovaný Inno Setup 6, aj
inštalátor.

## Namerané

Počítač s Ryzen 9 5950X a RTX 5080, snímka 1080p z plátna 4K, z angličtiny do slovenčiny, `translategemma:12b`:

- Čítanie celej snímky na grafike: asi 100 ms v hre (92 až 117 ms) a 255 až 395 ms v menu plnom textu. Na procesore
  s 8 vláknami: 290 až 340 ms a asi 565 ms.
- Čítanie len pásu okolo titulkov (60 % šírky, 15 % výšky): 68 až 86 ms v hre a 58 až 68 ms na obrazovke menu, kde celá
  snímka v tom istom meraní trvala 255 až 269 ms. V hre je zisk malý, lebo väčšinu času zaberie hľadanie textu, nie jeho
  množstvo.
- Viac oblastí sa poskladá vedľa seba do jedného obrázka a prečíta naraz. Merali sa len vtedy, keď grafiku zamestnávala
  iná hra, čo všetky časy asi zdvojnásobilo: dve oblasti vtedy trvali rovnako ako celá snímka v hre (150 až 270 ms oproti
  170 až 270 ms) a tri oblasti asi o štvrtinu menej na obrazovke menu (430 až 620 ms oproti 560 až 820 ms).
- Preklad: Ollama pri každej požiadavke strávi asi 0,35 s ešte pred prácou modelu. Cez Ollamu trval titulok 0,57 až 1,08 s
  (medián 0,64 s), priamo cez jej llama-server 0,14 až 0,72 s (medián 0,28 s) s rovnakými prekladmi. Okno potom ukázalo
  titulky 0,4 až 0,85 s po objavení. Krátke nápisy idú v dávkach; 5 položiek menu trvalo 0,4 s.
- OBS nevynechal žiadnu vykreslenú snímku v žiadnom behu s približne 3000 snímkami.
- Pamäť grafiky: 7,5 GB model, spolu asi 13 GB s OBS bez vysielania na plátne 4K.

## Čo sa skúšalo a čo nie

Skúšalo sa: štart a zastavenie z okna, zmena cieľového jazyka počas prekladu, výber jednej aj viacerých oblastí a návrat
na celý obraz počas prekladu, zostavený aj nainštalovaný program proti bežiacemu OBS, vytvorenie zdroja prekladu, tichá inštalácia
a odinštalovanie, stiahnutie prekladového modelu, automatický výber zdroja s hrou, štart po otvorení programu, zobrazenie
a skrytie klávesou a so skúšobným obrázkom v bežiacom OBS dva zdroje prekladu s oblasťou nakreslenou na inom mieste,
skrytie jedného zdroja, pridanie a odstránenie zdroja v editore vzhľadu a presunutie miesta oblasti v *Oblastiach na čítanie*.
Okná sa kontrolovali v tmavom aj svetlom režime na displeji 4K so zväčšením 125 %. Verzia 0.7.0: program po anglicky aj
po slovensky s prepnutím počas prekladu, výber modelu s uvoľnením predošlého, zväčšenie aj zmenšenie každého okna a pomer
strán presunutej oblasti pri kreslení aj v OBS. Verzia 0.8.0: naklonený text a pokojné preklady na 40 snímkach telefónu
pohybovaného ako v ruke a v bežiacom OBS s tým istým telefónom, ktorý otáčal a posúval skript, *OK* a *Použiť*
v *Oblastiach na čítanie* so zmenou oblastí počas prekladu, hranaté pozadie a tieň okolo písma.

Skúšalo sa len sčasti:

- Zapnutie servera WebSocket sa skúšalo na kópii súboru s nastaveniami OBS. Že OBS potom server zo zmeneného súboru
  naozaj spustí, vyplýva zo zdrojového kódu OBS; v skutočnom OBS sa to neskúšalo.
- Inštalácia Ollamy: stiahnutie z ollama.com a kontrola podpisu prebehli so skutočným inštalátorom a nepodpísaný súbor
  program odmietol. Samotný inštalátor sa nespustil, lebo skúšobný počítač už Ollamu má.
- Klávesa na zobrazenie a skrytie: registrácia klávesy vo Windows a reakcia na ňu sa skúšali poslaním správy o klávese
  programu, nie stlačením klávesy.

Neskúšalo sa: čítanie textu na procesore v zostavenom programe, iná grafika než RTX 5080, Windows 10, iná verzia OBS
než 33 a celé živé vysielanie. Oblasti v skúškach kreslil skript, ktorý simuluje myš, nie ruka.

## Hranice

- Pôvodný text presvitá cez polopriehľadné pozadie. Krytie pozadia 100 % vo *Vzhľade prekladov* dá plné pozadie.
- Preklad je taký dobrý, aký je lokálny model. Slang občas netrafí a názov značky, ktorý vyzerá ako slovo, vie preložiť
  nezmyslom.
- Preklad dlhší než originál sa zmenší najviac na 70 % pôvodnej veľkosti a potom presiahne cez susedov.
- Text, ktorý sa rýchlo hýbe, sa neprekladá; text vo svete hry sa preloží, keď kamera spomalí.
- Naklonený text sa kreslí v jeho uhle, ale rovno: preklad je otočený obdĺžnik, nie v perspektíve.
- Chránené video, ktoré OBS ukazuje ako čierny obraz, sa prečítať nedá.
- Po odinštalovaní ostanú nastavenia a uložené preklady v `%APPDATA%\OBS Screen Translator`.

## Licencia

MIT, pozri [LICENSE](LICENSE). Repozitár obsahuje len vlastný kód projektu. Inštalátor pribaľuje softvér tretích strán pod
jeho vlastnými licenciami; pozri [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md). Projekt nie je spojený s OBS Project,
Google, Ollama, Microsoftom ani so žiadnym vydavateľom hier.
