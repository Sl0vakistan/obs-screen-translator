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

1. Nainštalujte [OBS Studio](https://obsproject.com/) 28 alebo novší a zapnite *Nástroje > Nastavenia servera WebSocket >
   Povoliť server WebSocket*.
2. Nainštalujte [Ollamu](https://ollama.com/download). Beží v nej prekladový model.
3. Zo stránky Releases tohto repozitára stiahnite `OBS-Screen-Translator-Setup-<verzia>.exe` a spustite ho. Inštaluje sa
   pre aktuálneho používateľa, bez práv správcu.

Inštalátor nie je podpísaný, takže Windows SmartScreen môže upozorniť na neznámeho vydavateľa; pokračuje sa cez *Ďalšie
informácie > Spustiť aj tak*. Ak nepodpísaný inštalátor spúšťať nechcete, spustite program zo zdrojového kódu (nižšie).

## Použitie

1. Spustite OBS a potom *OBS Screen Translator* z ponuky Štart.
2. Vyberte jazyky v **Translate from** (z akého) a **Translate to** (do akého).
3. V **Game source in OBS** vyberte zdroj s hrou. *Refresh* načíta zoznam zdrojov z OBS znova.
4. Voliteľne **Area to read** (výrez). *Choose...* ukáže aktuálny obraz hry; myšou potiahnite obdĺžnik okolo časti, ktorú
   chcete prekladať, napríklad len okolo titulkov, a stlačte *Use this area*. Text mimo obdĺžnika sa ignoruje.
   *Whole picture* v tom istom okne vráti celý obraz.
5. Stlačte **Start**.

Pri prvom spustení si program stiahne prekladový model (8,1 GB, raz) a do scény, ktorá práve ide do vysielania, pridá zdroj
prehliadača *Translation overlay*. Okno vypisuje každý preložený text a čas, ktorý to trvalo.

Jazyk zmeníte výberom iného v okne. Preklad sa v novom jazyku spustí sám, netreba ho predtým zastavovať. Každý jazyk má
vlastné uložené preklady. Rovnako sa počas prekladu dá zmeniť výrez.

Menší výrez znamená menej čítania a menej prekladania. Najviac pomôže na obrazovkách plných textu a vtedy, keď vás zaujíma
len jedna časť obrazu, napríklad titulky; pozri *Namerané*.

Program pracuje, len kým je zdroj prekladu viditeľný v scéne, ktorá ide do vysielania. Keď zdroj skryjete, prestane čítať
aj prekladať. Na prepínanie jednou klávesou dajte v OBS (*Nastavenia > Klávesové skratky*) akciám *Zobraziť* a *Skryť* tohto
zdroja tú istú klávesu. Zdroj prekladu musí byť priamo v scéne, nie vo vnorenej scéne.

Zavretím okna preklady z obrazu zmiznú.

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
- OBS Studio 28 alebo novší so zapnutým WebSocket serverom.
- Ollama. Model `translategemma:12b` potrebuje asi 7,5 GB pamäte grafiky; `translategemma:4b` asi 2,7 GB a prekladá citeľne
  horšie.
- Grafická karta s DirectX 12 na čítanie textu. Bez nej čítanie beží na procesore a zamestná niekoľko jadier.

## Jazyky

V zoznamoch je 164 položiek: 160 základných jazykov z tabuľky jazykov TranslateGemma, filipínčina, brazílska portugalčina
a zjednodušená a tradičná čínština. Google uvádza, že model je stavaný pre 55 jazykov, takže menej bežné budú slabšie. Na streame sa skúšala len
angličtina do slovenčiny.

Čítanie textu pozná latinku a čínštinu. Hra v inom písme (cyrilika, arabské písmo, kórejčina a ďalšie) sa zatiaľ neprečíta
správne, nech vyberiete akýkoľvek jazyk.

## Nastavenia

Jazyky, zdroj s hrou a výrez sa nastavujú v okne. Všetko ostatné je v súbore `settings.json`, ktorý vznikne pri prvom spustení
v `%APPDATA%\OBS Screen Translator` (pri spustení zo zdrojového kódu vedľa `translator.py`). Zmeny platia po novom spustení
programu. Tabuľka všetkých položiek je v [README.md](README.md#settings). Najdôležitejšie:

- `context` – jedna alebo dve anglické vety, ktoré modelu povedia, aký text dostáva a ako má čitateľa oslovovať. Pri
  preklade dialógov do slovenčiny pomôže dopísať: `Dialogue is colloquial and informal: address a single person as 'ty',
  never the formal 'vy'.`
- `model` – `translategemma:12b` alebo `translategemma:4b`; `ollama_url` môže ukazovať aj na iný počítač.
- `ocr_on_gpu` – `false` presunie čítanie textu na procesor.

Krytie pozadia sa mení v adrese zdroja prehliadača: `&opacity=1` na konci adresy dá úplne čierne pozadie.

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
- Preklad: titulok 0,5 až 1 s po objavení. Ollama pridáva ku každému volaniu asi 0,35 s, preto idú krátke nápisy v dávkach;
  12 položiek menu trvalo 1,3 s.
- OBS nevynechal žiadnu vykreslenú snímku v žiadnom behu s približne 3000 snímkami.
- Pamäť grafiky: 7,5 GB model, spolu asi 13 GB s OBS bez vysielania na plátne 4K.

## Čo sa skúšalo a čo nie

Skúšalo sa: štart a zastavenie z okna, zmena cieľového jazyka počas prekladu, výber výrezu a návrat na celý obraz počas
prekladu, zostavený aj nainštalovaný program proti bežiacemu OBS, vytvorenie zdroja prekladu, tichá inštalácia
a odinštalovanie.

Neskúšalo sa: počítač bez Ollamy alebo bez modelu (sťahovanie pri prvom spustení), čítanie textu na procesore v zostavenom
programe, iná grafika než RTX 5080, Windows 10 a celé živé vysielanie.

## Hranice

- Pôvodný text presvitá cez polopriehľadné pozadie. `opacity=1` dá plné pozadie.
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
