# OBS Screen Translator

Živý preklad textu z obrazu pre streamerov. Program číta text v zdroji [OBS Studio](https://obsproject.com/) (hra zo
zachytávacej karty, zachytenie hry, okno), preloží ho jazykovým modelom, ktorý beží vo vašom počítači, a preklad nakreslí
cez pôvodný text na čiernom polopriehľadnom pozadí. Diváci vidia titulky, správy, pokyny a menu vo svojom jazyku; z počítača
nič neodchádza.

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
  (1,9 GB) a nainštaluje. Stiahnutý inštalátor spustí len vtedy, keď má podpis Ollamy.
- Prekladový model (8,1 GB) sa stiahne raz.

Prvé dve veci môžete spraviť aj ručne: v OBS *Nástroje > Nastavenia servera WebSocket > Povoliť server WebSocket*
a inštalátor z [ollama.com/download](https://ollama.com/download).

Inštalátor nie je podpísaný, takže Windows SmartScreen môže upozorniť na neznámeho vydavateľa; pokračuje sa cez *Ďalšie
informácie > Spustiť aj tak*. Ak nepodpísaný inštalátor spúšťať nechcete, spustite program zo zdrojového kódu (nižšie).

## Použitie

1. Spustite OBS a *OBS Screen Translator* z ponuky Štart, v ľubovoľnom poradí. Program na OBS počká.
2. Skontrolujte jazyky v **Translate from** (z akého) a **Translate to** (do akého). Cieľový jazyk je na začiatku jazyk
   vášho Windows.
3. Skontrolujte **Game source in OBS**. Ak je v scéne, ktorá ide do vysielania, práve jedna zachytávacia karta, vyberie sa
   sama; rovnako jediné zachytenie hry, okna alebo obrazovky. Inak vyberte hru zo zoznamu. *Refresh* načíta zoznam zdrojov
   z OBS znova.
4. Voliteľne **Area to read** (oblasti na čítanie). *Choose...* ukáže aktuálny obraz hry; myšou potiahnite obdĺžnik
   okolo každej časti, ktorú chcete prekladať, napríklad okolo titulkov a telefónu. Obdĺžnikov môže byť viac. Text mimo
   nich sa ignoruje. *Remove last* odoberie posledný, *Remove all* všetky; bez obdĺžnika sa číta celý obraz. *Use*
   výber potvrdí.
5. Voliteľne **Background opacity** (krytie pozadia). Ťahadlo určuje, aké tmavé je pozadie za prekladom, od žiadneho
   (0 %) po úplne čierne (100 %). Preklady, ktoré sú práve na obraze, sa menia už počas ťahania.
6. Voliteľne **Show/hide key** (klávesa na zobrazenie a skrytie). Stlačte *Set...* a potom funkčnú klávesu (F1 až F24)
   alebo kombináciu s Ctrl či Alt. Tá klávesa preklady zobrazí a skryje, nech je v popredí ktorékoľvek okno, aj keď ju
   pošle Stream Deck.
7. Stlačte **Start**. Keď zaškrtnete **Start translating when this program opens**, nabudúce to program spraví za vás.

Pri prvom spustení program do scény, ktorá práve ide do vysielania, pridá zdroj prehliadača *Translation overlay*.

V ponuke **Help** je krátky návod (*Installation and setup*, po anglicky), *Details* s verziou, licenciou a miestom
nastavení a uložených prekladov, *Open the settings folder* (otvorí zložku s nastaveniami) a odkaz na tento projekt. Okno vypisuje každý preložený text a čas, ktorý to trvalo.

Jazyk zmeníte výberom iného v okne. Preklad sa v novom jazyku spustí sám, netreba ho predtým zastavovať. Každý jazyk má
vlastné uložené preklady. Rovnako sa počas prekladu dajú zmeniť oblasti.

Menšie oblasti znamenajú menej čítania a menej prekladania a žiadne preklady cez časti obrazu, ktoré vás nezaujímajú.
Najviac pomôžu na obrazovkách plných textu; pozri *Namerané*.

Program pracuje, len kým je zdroj prekladu viditeľný v scéne, ktorá ide do vysielania. Keď zdroj skryjete, prestane čítať
aj prekladať. Klávesa z okna programu robí presne toto, vo všetkých scénach, kde zdroj prekladu je. Zdroj prekladu musí
byť priamo v scéne, nie vo vnorenej scéne.

Zavretím okna preklady z obrazu zmiznú a prekladový model sa hneď uvoľní z grafickej karty. Kým program beží, Ollama
drží model načítaný aj medzi prekladmi.

## Ako to pracuje

1. Štyrikrát za sekundu si program cez vstavaný WebSocket server vypýta od OBS snímku zdroja s hrou.
2. [RapidOCR](https://github.com/RapidAI/RapidOCR) (modely PP-OCR) nájde a prečíta text v celej snímke. Beží na grafickej
   karte cez DirectML, ktorý funguje na každej karte s DirectX 12, alebo na procesore.
3. Riadky, ktoré patria k sebe (dvojriadkový titulok, odsek správy), sa spoja do jedného bloku.
4. Blok preloží [TranslateGemma](https://ollama.com/library/translategemma) cez Ollamu. Vety idú po jednej hneď, ako sa
   objavia; krátke nápisy, napríklad položky menu, v dávkach do 12 kusov.
5. Zdroj prehliadača v OBS (`overlay.html`) dostane preklady cez lokálny WebSocket a každý nakreslí na miesto textu, ktorý
   nahrádza.

Do modelu ide len nový text. Text, ktorý na obraze ostáva, sa preloží raz, a každý preklad sa ukladá na disk, takže menu,
ktoré už program videl, sa ukáže hneď, aj po reštarte.

Preklad sa zobrazí, až keď sa text dvakrát po sebe prečíta na tom istom mieste. Text, ktorý sa hýbe s kamerou (nápisy a
značky áut vo svete hry), preto ostáva bez prekladu, kým obraz nezastane.

## Čo treba

- Windows 10 alebo 11, 64-bitový. Program vznikol a bol skúšaný len na Windows 11.
- OBS Studio. Program vznikol a bol skúšaný s OBS 33. Nastavenia servera WebSocket číta zo súboru
  `plugin_config\obs-websocket\config.json`; verzie OBS, ktoré ich ešte držia v `global.ini`, nie sú podporované.
- Ollama; program ju vie nainštalovať. Model `translategemma:12b` potrebuje asi 7,5 GB pamäte grafiky; `translategemma:4b` asi 2,7 GB a prekladá citeľne
  horšie.
- Grafická karta s DirectX 12 na čítanie textu. Bez nej čítanie beží na procesore a zamestná niekoľko jadier.

## Jazyky

V zoznamoch je 164 položiek: 160 základných jazykov z tabuľky jazykov TranslateGemma, filipínčina, brazílska portugalčina
a zjednodušená a tradičná čínština. Google uvádza, že model je stavaný pre 55 jazykov, takže menej bežné budú slabšie. Na streame sa skúšala len
angličtina do slovenčiny.

Čítanie textu pozná latinku a čínštinu. Hra v inom písme (cyrilika, arabské písmo, kórejčina a ďalšie) sa zatiaľ neprečíta
správne, nech vyberiete akýkoľvek jazyk.

## Nastavenia

Jazyky, zdroj s hrou, oblasti na čítanie, krytie pozadia, klávesa na zobrazenie a skrytie a automatický štart sa nastavujú v okne. Všetko ostatné je v súbore `settings.json`, ktorý vznikne pri prvom spustení
v `%APPDATA%\OBS Screen Translator` (pri spustení zo zdrojového kódu vedľa `translator.py`). Zmeny platia po novom spustení
programu. Tabuľka všetkých položiek je v [README.md](README.md#settings). Najdôležitejšie:

- `context` – jedna alebo dve anglické vety, ktoré modelu povedia, aký text dostáva a ako má čitateľa oslovovať. Pri
  preklade dialógov do slovenčiny pomôže dopísať: `Dialogue is colloquial and informal: address a single person as 'ty',
  never the formal 'vy'.`
- `model` – `translategemma:12b` alebo `translategemma:4b`; `ollama_url` môže ukazovať aj na iný počítač.
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
- Preklad: titulok 0,5 až 1 s po objavení. Ollama pridáva ku každému volaniu asi 0,35 s, preto idú krátke nápisy v dávkach;
  12 položiek menu trvalo 1,3 s.
- OBS nevynechal žiadnu vykreslenú snímku v žiadnom behu s približne 3000 snímkami.
- Pamäť grafiky: 7,5 GB model, spolu asi 13 GB s OBS bez vysielania na plátne 4K.

## Čo sa skúšalo a čo nie

Skúšalo sa: štart a zastavenie z okna, zmena cieľového jazyka počas prekladu, výber jednej aj viacerých oblastí a návrat
na celý obraz počas prekladu, zostavený aj nainštalovaný program proti bežiacemu OBS, vytvorenie zdroja prekladu, tichá inštalácia
a odinštalovanie, stiahnutie prekladového modelu, automatický výber zdroja s hrou, štart po otvorení programu a zobrazenie
a skrytie klávesou.

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

- Pôvodný text presvitá cez polopriehľadné pozadie. Ťahadlo **Background opacity** na 100 % dá plné pozadie.
- Preklad je taký dobrý, aký je lokálny model. Slang občas netrafí a názov značky, ktorý vyzerá ako slovo, vie preložiť
  nezmyslom.
- Preklad dlhší než originál sa zmenší najviac na 70 % pôvodnej veľkosti a potom presiahne cez susedov.
- Text, ktorý sa hýbe, sa neprekladá; text vo svete hry sa preloží, keď kamera stojí.
- Chránené video, ktoré OBS ukazuje ako čierny obraz, sa prečítať nedá.
- Po odinštalovaní ostanú nastavenia a uložené preklady v `%APPDATA%\OBS Screen Translator`.

## Licencia

MIT, pozri [LICENSE](LICENSE). Repozitár obsahuje len vlastný kód projektu. Inštalátor pribaľuje softvér tretích strán pod
jeho vlastnými licenciami; pozri [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md). Projekt nie je spojený s OBS Project,
Google, Ollama, Microsoftom ani so žiadnym vydavateľom hier.
