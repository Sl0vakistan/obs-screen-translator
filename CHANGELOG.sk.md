# Zoznam zmien

Anglická verzia: [CHANGELOG.md](CHANGELOG.md). Do verzie 0.6.0 bol program len po anglicky, preto sú názvy v okne pri
starších verziách anglické.

## 0.7.0 - 2026-11-20

- **Po slovensky**: celý program je aj po slovensky, vrátane návodu, podrobností a zoznamu zmien. Tlačidlo vedľa
  *Pomocníka* prepína medzi angličtinou a slovenčinou hneď; kým si nevyberiete, program sa riadi jazykom Windows. Uložené
  ako `ui_language`.
- **Model v okne**: *Preklad* → *Model* vyberá medzi TranslateGemma 12b (najlepšie preklady, asi 7,5 GB pamäte grafiky)
  a 4b (slabšie, asi 2,7 GB). Riadok pod ním ukazuje grafickú kartu počítača a jej pamäť. Model, ktorý na počítači ešte
  nie je, sa stiahne pri ďalšom stlačení *Spustiť* a doterajší model sa uvoľní z grafickej karty.
- **Každé okno sa dá zväčšiť aj zmenšiť**. V *Oblastiach na čítanie* sa obraz prispôsobí veľkosti okna a drží pomer strán
  zdroja v OBS; z OBS sa berie so šírkou 1920 bodov, takže ostane ostrý aj vo veľkom okne.
- **Miesto presunutej oblasti drží pomer strán**: modrý obdĺžnik pri ťahaní drží tvar svojej žltej oblasti, takže preklad
  sa nikdy nezúži ani nenatiahne. Miesto nakreslené vo verzii 0.6.0 s iným pomerom preklad vyplní, nakoľko sa doň zmestí,
  a to na stred.

## 0.6.0 - 2026-11-20

- **Oblasti ukázané inde**: oblasť sa môže čítať na jednom mieste a jej preklad kresliť na inom (*Areas to read* →
  *Draw where area N is shown*). Preklad sa tam presunie a prispôsobí veľkosti nového obdĺžnika.
- **Viac zdrojov prekladu v OBS**: *Look of translations* → *Shown in OBS source* pošle oblasť do vlastného zdroja
  prehliadača. *New source...* ho v OBS vytvorí, *Remove source* ho odstráni. Každý zdroj sa dá v OBS samostatne
  umiestniť, orezať, dať mu filtre a zobraziť či skryť; oblasti skrytého zdroja sa nečítajú. Klávesa na zobrazenie
  a skrytie prepína všetky.
- **Nový vzhľad okien**: štýl Windows 11 (téma Sun Valley), tmavý alebo svetlý podľa nastavenia Windows, nastavenia
  rozdelené do sekcií a záhlavia okien vo farbe okna. *Help* je tlačidlo vpravo hore.
- **Vzhľad prekladov** (*Edit...* v okne, nahrádza ťahadlo krytia): písmo, veľkosť (ako pôvodný text alebo pevná), tučné,
  kurzíva, farba textu, farba a krytie pozadia, obrys a zarovnanie.
- Jeden predvolený vzhľad pre všetky oblasti; každá oblasť ho môže ponechať alebo dostať vlastný (*Settings for*
  v editore).
- Kým je editor otvorený, OBS ukazuje vzorový preklad s upravovaným vzhľadom; zmeny platia hneď, aj pre preklady na
  obraze.
- *Help* → *What's new in 0.6.0* ukazuje zmeny nainštalovanej verzie.
- Návod (*Help* → *Installation and setup*) a README vysvetľujú, ako sprevádzkovať Ollamu. Ollama po inštalácii otvorí
  vlastné okno s príkazmi do terminálu (*Launch*); prekladač ich nepotrebuje a hneď po inštalácii Ollamy to napíše do
  svojho okna.
- Nastavenia: `style` drží predvolený vzhľad a `overlays` zoznam zdrojov prekladu (nahrádza `overlay_source`); každá
  položka `regions` je teraz `{"box": [...], "style": null alebo vzhľad, "display": null alebo obdĺžnik, "overlay": 0}`.
  Nastavenia z verzie 0.5.0 (`opacity`, `overlay_source`, oblasti ako obyčajné zoznamy) sa prevedú pri prvom spustení.
- Adresa zdroja prekladu obsahuje verziu, takže OBS po aktualizácii načíta novú stránku.
- Preklady sa ukážu asi o tretinu sekundy skôr. Ollama pri každej požiadavke strávi asi 0,35 s ešte pred prácou modelu.
  Po prvej odpovedi program posiela text priamo llama-serveru, ktorý Ollama pre model spustila, so šablónou a nastaveniami,
  aké by použila Ollama. Robí to len vtedy, keď skúšobná veta vyjde presne ako cez Ollamu, a keď to spojenie zlyhá, vráti
  sa k Ollame. Ollama naďalej model načítava, drží a uvoľňuje; program jej každých päť minút pripomenie, že sa model
  používa. Okno ukazovalo titulky 0,4 až 0,85 s po objavení, predtým 1,2 až 1,5 s.

## 0.5.0 - 2026-11-20

Program si väčšinu vecí nastaví sám, takže inštalácia sa zúži na inštalátor a tlačidlo Start.

- Ak je server WebSocket v OBS vypnutý, program ponúkne, že ho zapne. Počká, kým sa OBS zavrie, zmení nastavenie
  a doterajšie nechá v súbore `config.before-screen-translator.json`.
- Ak chýba Ollama, program ponúkne, že ju stiahne z ollama.com a nainštaluje. Stiahnutý inštalátor spustí len vtedy, keď
  má podpis Ollamy.
- Zdroj s hrou sa vyberie automaticky, keď je v scéne, ktorá ide do vysielania, práve jedna zachytávacia karta,
  zachytenie hry, okna alebo obrazovky.
- Pri prvom spustení je cieľový jazyk jazyk Windows.
- **Show/hide key**: klávesa alebo kombinácia kláves nastavená v okne, ktorá odkiaľkoľvek zobrazí a skryje preklady, aj
  zo Stream Decku. Uložená ako `hotkey`.
- **Start translating when this program opens**. Uložené ako `start_automatically`.
- **Background opacity**: ťahadlo v okne od žiadneho pozadia (0 %) po úplne čierne (100 %). Preklady na obraze sa menia
  hneď. Uložené ako `opacity`; `opacity` v adrese zdroja prekladu sa už nepoužíva.
- Ponuka **Help**: *Installation and setup* (krátky návod v programe), *Details* (verzia, licencia, ako to pracuje, kde
  sú nastavenia a uložené preklady), *Open the settings folder* a *Project page*.
- Program čaká na OBS a pripojí sa hneď, ako beží; *Refresh* na to už netreba.
- Zavretím okna sa prekladový model hneď uvoľní z grafickej karty. Predtým ho Ollama držala ešte 30 minút po poslednom
  preklade.

## 0.4.1 - 2026-11-20

- Menší inštalátor. Zostavenie vynecháva tri časti, ktoré program nikdy nepoužíva: knižnicu na video z OpenCV, modul AVIF
  z Pillow a model na otáčanie textu. Na fungovaní programu sa nič nemení.

## 0.4.0 - 2026-11-20

- Viac oblastí na čítanie: v okne *Area to read* sa dá nakresliť ľubovoľný počet obdĺžnikov; *Remove last* a *Remove all*
  ich odoberú a bez obdĺžnika sa číta celý obraz. Všetky oblasti sa poskladajú do jedného obrázka a prečítajú naraz.
- Nastavenie je teraz `regions`, zoznam oblastí. `region` z verzie 0.3.0 sa prevedie pri prvom spustení.
- Okno napíše, že pripravuje prekladový model, čo môže po jeho uvoľnení chvíľu trvať.

## 0.3.0 - 2026-11-20

- Oblasť na čítanie: *Choose...* v okne ukáže aktuálny obraz zdroja s hrou a dovolí potiahnuť obdĺžnik okolo časti, ktorá
  sa má prekladať. Číta sa len tá časť; text mimo nej sa ignoruje. *Whole picture* vráti celý obraz. Oblasť sa dá meniť
  aj počas prekladu. V `settings.json` je uložená ako `region`.
- `--preview` vyznačí oblasť v `preview.png`.

## 0.2.0 - 2026-11-20

- Program má okno: jazyky sa vyberajú zo zoznamov (164 položiek z tabuľky jazykov TranslateGemma), zdroj s hrou zo
  zoznamu zdrojov v OBS a Start a Stop sú tlačidlá. Zmena jazyka počas prekladu preklad reštartuje v novom jazyku.
- Inštalátor `OBS-Screen-Translator-Setup-<verzia>.exe` (Inno Setup, pre používateľa, bez práv správcu), ktorý zostaví
  `build.ps1` z balíka PyInstaller. Na používanie programu už netreba Python.
- Text sa číta na grafickej karte cez DirectML (`onnxruntime-directml`) namiesto PyTorchu s CUDA, takže funguje každá
  karta s DirectX 12 a balík ostáva malý. Ak to zlyhá, použije sa procesor.
- `settings.json` vznikne pri prvom spustení (pri nainštalovanom programe v `%APPDATA%\OBS Screen Translator`);
  `settings.example.json` zmizol. Jazyky sa ukladajú ako kódy.
- Pri štarte program spustí Ollamu, ak je nainštalovaná a nebeží, a stiahne prekladový model, ak chýba. Problémy ako
  chýbajúca Ollama alebo OBS hlási v okne.
- Adresa zdroja prekladu sa udržiava aktuálna, takže zdroj prežije preinštalovanie do inej zložky.
- README otvorene píše, že projekt vznikol vibe codingom.

## 0.1.0 - 2026-11-19

Prvé verejné vydanie.

- `translator.py`: číta snímky zdroja v OBS cez server WebSocket v OBS, nájde text v celej snímke cez RapidOCR (grafika
  cez PyTorch a CUDA alebo procesor), spojí riadky do blokov a preloží ich modelom TranslateGemma, ktorý beží v Ollame.
- Preklady sa posielajú cez lokálny WebSocket a kreslí ich `overlay.html`, zdroj prehliadača v OBS, cez pôvodný text na
  čiernom polopriehľadnom pozadí.
- Prekladá sa len nový text; preklady sa ukladajú na disk. Krátke nápisy sa prekladajú v dávkach.
- Preklad sa ukáže, až keď sa jeho text dvakrát prečíta na tom istom mieste, takže text, ktorý sa vo svete hry hýbe, sa
  preskočí.
- Zdroj prekladu vznikne pri prvom spustení. Keď je skrytý, čítanie aj preklad sa pozastavia.
- `--preview`, `--image` a `--settings`; `settings.example.json` so zdrojovým a cieľovým jazykom, vetou o kontexte,
  modelom a prahmi čítania.
