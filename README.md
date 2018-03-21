# PoliTo Advanced Downloader
Script che permette di cercare tutte le videolezioni disponibili per il download.

## Installazione
#### Requisiti
* Python 3
* Modulo requests: `$ pip install requests` oppure `$ pip3 install requests`

#### Selezione cartella download
In `main.py` modificare il parametro `sess.setDlFolder` scegliendo la cartella di destinazioni per le videolezioni scaricate.

#### Esecuzione
Eseguire `$ python main.py` oppure `$ python3 main.py` oppure fare doppio click su `main.py`.

Il programma chiederà i vostri dati di accesso al sito polito.it dopodiché effettuerà il _crawling_ di tutte le videolezioni disponibili nell'intervallo impostato.

## Funzioni avanzate
Se il programma non dovesse visualizzare tutte le videolezioni nel vostro corso (in particolare le più recenti) è necessario agire sull'intervcallo di crawling e, in particolare, in `main.py` aumentare il secondo valore di `sess.setInterval`

Se non vi compare un corso o un professore dopo aver già effettuato il crawling è necessario cancellare il file `crawled.bin` e rieseguire il programma.

## Crediti
Grazie a [gius-italy](https://github.com/gius-italy) per lo script del login e del download!
