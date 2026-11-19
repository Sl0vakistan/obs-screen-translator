# OBS Screen Translator

Živý preklad textu z obrazu pre streamerov. Nástroj číta text v zdroji [OBS Studio](https://obsproject.com/) (hra zo
zachytávacej karty, zachytenie hry, okno), preloží ho jazykovým modelom, ktorý beží vo vašom počítači, a preklad nakreslí
cez pôvodný text na čiernom polopriehľadnom pozadí. Diváci vidia titulky, správy, pokyny a menu vo svojom jazyku; z počítača
nič neodchádza.

English version: [README.md](README.md)

Otvorený zdrojový kód pod licenciou MIT, pozri [LICENSE](LICENSE).

## Ako to pracuje

1. Štyrikrát za sekundu si nástroj cez vstavaný WebSocket server vypýta od OBS snímku zdroja s hrou.
2. [RapidOCR](https://github.com/RapidAI/RapidOCR) (modely PP-OCR) nájde a prečíta text v celej snímke, na grafike alebo na
   procesore.
3. Riadky, ktoré patria k sebe (dvojriadkový titulok, odsek správy), sa spoja do jedného bloku.
4. Blok preloží [TranslateGemma](https://ollama.com/library/translategemma) cez [Ollamu](https://ollama.com/). Vety idú po
   jednej hneď, ako sa objavia; krátke nápisy, napríklad položky menu, v dávkach do 12 kusov.
5. Zdroj prehliadača v OBS (`overlay.html`) dostane preklady cez lokálny WebSocket a každý nakreslí na miesto textu, ktorý
   nahrádza.

Do modelu ide len nový text. Text, ktorý na obraze ostáva, sa preloží raz, a každý preklad sa ukladá do súboru, takže menu,
ktoré už nástroj videl, sa ukáže hneď, aj po reštarte.

Preklad sa zobrazí, až keď sa text dvakrát po sebe prečíta na tom istom mieste. Text, ktorý sa hýbe s kamerou (nápisy a
značky áut vo svete hry), preto ostáva bez prekladu, kým obraz nezastane.

## Čo treba

- Windows 10 alebo 11. Nástroj vznikol a bol skúšaný len na Windows 11.
- OBS Studio 28 alebo novší so zapnutým WebSocket serverom (*Nástroje > Nastavenia servera WebSocket*).
- Python 3.10 alebo novší.
- Ollama s modelom TranslateGemma. `translategemma:12b` potrebuje asi 7,5 GB pamäte grafiky, `translategemma:4b` asi 2,7 GB
  a prekladá citeľne horšie.
- Voliteľne grafika NVIDIA a PyTorch s CUDA na čítanie textu grafikou. Bez toho čítanie beží na procesore a zamestná
  niekoľko jadier.

## Inštalácia

```
py -3 -m pip install -r requirements.txt
ollama pull translategemma:12b
copy settings.example.json settings.json
```

Na čítanie textu grafikou nainštalujte PyTorch s CUDA podľa [pytorch.org](https://pytorch.org/get-started/locally/). Inak
v `settings.json` nastavte `ocr_on_gpu` na `false`.

V `settings.json` nastavte `obs_source` na názov zdroja OBS, ktorý ukazuje hru.

Pri prvom spustení sa stiahnu modely na čítanie textu (desiatky megabajtov).

## Použitie

Spustite OBS a potom `start-translator.cmd`. Pri prvom spustení nástroj pridá zdroj prehliadača *Translation overlay* do
aktuálnej scény alebo do scén uvedených v `scenes`. Okno nechajte otvorené; vypisuje každý preložený text a čas, ktorý to
trvalo. Zavretím okna preklady z obrazu zmiznú.

Nástroj pracuje, len kým je zdroj prekladu viditeľný v scéne, ktorá ide do vysielania. Keď zdroj skryjete, prestane čítať
aj prekladať. Na prepínanie jednou klávesou dajte v OBS (*Nastavenia > Klávesové skratky*) akciám *Zobraziť* a *Skryť* tohto
zdroja tú istú klávesu.

Zdroj prekladu musí byť priamo v scéne, nie vo vnorenej scéne.

Skúška bez vysielania:

```
start-translator.cmd --preview
```

Prečíta jednu snímku z OBS, vypíše nájdené texty s prekladom a uloží `preview.png` s vyznačenými textami. `--image
subor.png` spraví to isté pre obrázok z disku, `--settings cesta` vyberie iný súbor nastavení, napríklad pre každú hru
vlastný.

## Nastavenia

Všetky položky `settings.json` s predvolenými hodnotami sú v tabuľke v [README.md](README.md#settings). Najdôležitejšie:

- `obs_source` – názov zdroja OBS, z ktorého sa číta.
- `source_language`, `target_language` – z akého jazyka do akého (názov po anglicky a kód).
- `context` – jedna alebo dve anglické vety, ktoré modelu povedia, aký text dostáva a ako má čitateľa oslovovať. Pri
  preklade dialógov do slovenčiny pomôže dopísať: `Dialogue is colloquial and informal: address a single person as 'ty',
  never the formal 'vy'.`
- `model` – `translategemma:12b` alebo `translategemma:4b`; `ollama_url` môže ukazovať aj na iný počítač.
- `ocr_on_gpu` – `false` presunie čítanie textu na procesor.

Krytie pozadia sa mení v adrese zdroja prehliadača: `overlay.html?scale=2&opacity=1` je úplne čierne pozadie.

## Namerané

Počítač s Ryzen 9 5950X a RTX 5080, snímka 1080p z plátna 4K, z angličtiny do slovenčiny, `translategemma:12b`:

- Čítanie celej snímky: 64 ms v hre a do 180 ms v menu plnom textu na grafike; 190 až 470 ms na procesore s 8 vláknami,
  čo zamestnalo asi 7 jadier.
- Preklad: titulok 0,5 až 1 s po objavení. Ollama pridáva ku každému volaniu asi 0,35 s, preto idú krátke nápisy v dávkach;
  12 položiek menu trvalo 1,3 s.
- OBS nevynechal žiadnu vykreslenú snímku v žiadnom behu s približne 3000 snímkami.
- Pamäť grafiky: 7,5 GB model, spolu asi 13 GB s OBS bez vysielania na plátne 4K.

## Hranice

- Pôvodný text presvitá cez polopriehľadné pozadie. `opacity=1` dá plné pozadie.
- Preklad je taký dobrý, aký je lokálny model. Slang občas netrafí a názov značky, ktorý vyzerá ako slovo, vie preložiť
  nezmyslom.
- Preklad dlhší než originál sa zmenší najviac na 70 % pôvodnej veľkosti a potom presiahne cez susedov.
- Predvolený model čítania pozná latinku a čínštinu. Iné písma potrebujú iný rozpoznávací model RapidOCR.
- Text, ktorý sa hýbe, sa neprekladá; text vo svete hry sa preloží, keď kamera stojí.
- Chránené video, ktoré OBS ukazuje ako čierny obraz, sa prečítať nedá.

## Licencia

MIT, pozri [LICENSE](LICENSE). Projekt neobsahuje cudzí kód, modely ani obsah hier; čo si sťahuje a používa za behu, je
v [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md). Projekt nie je spojený s OBS Project, Google, Ollama ani so žiadnym
vydavateľom hier.
