# Štruktúra

## Moduly
Rôzne dokumenty sa musia buildovať podľa rozličných templatov.

## Štýly

### Semináre

### Náboj
Náboj má targety

- booklet
- tearoff

## Metadáta


### Matematika
HTML 

### SI jednotky
Na všetky fyzikálne jednotky používame package `siunitx`. Všetky fyzikálne znaky musia byť kvôli MathJAXu vždy vnútri matematiky `$...$`. Siunitx pozná príkazy

- `\SI{koľko}{čoho}`, napríklad $\SI{6.67e-11}{\cubic\metre\per\kilo\gram\per\second\squared}$. Pozná aj \pm, teda dá sa vložiť odchýlka.
- `\si{jednotka}` pre prípad, keď nepotrebujeme hodnotu, ale stačí jednotka
- `\num{číslo}` vie formátovať čísla, napríklad $\num{3.64e56}$ vyrenderuje pekne 3,64 . 10^16
- `\ang{1;24;30}` pre uhly (desatinné číslo, alebo minúty a sekundy)

### Obrázky

Momentálne používame mierne nešťastnú custom syntax:

`@P{názov bez prípony}{prípona pre PDF}{prípona pre web}{výška obrázka pre PDF}{popis}{label}`

Časom by z toho chcelo byť niečo štandardné.

### Odkazy
Klasická markdownová syntax:

    [odkaz](http://odkaz.com/)

alebo ak sa má zobraziť skutočná URL:
    
    <http://odkaz.com/>

### 
