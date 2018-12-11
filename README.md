# PoliTo Advanced Downloader
Script che permette di cercare, scaricare e mantenere aggiornate tutte le videolezioni disponibili per il download.

## Installazione
#### Requisiti
* [Python 3](https://www.python.org/downloads/)
* **Importante!** Installare le dipendenze con: `$ pip install -r requirements.txt` oppure `$ pip3 install -r requirements.txt`

## Esecuzione
#### Modifica delle impostazioni
* Rinominare il file `settings.json.dist` in `settings.json`
* Aprire `settings.json`
* Modificare la cartella di download

Se si vuole abilitare l'accesso automatico è sufficiente scrivere *true* al posto di *false* e completare
con le proprie credenziali il file.

#### Esecuzione
Eseguire `$ python main.py` oppure `$ python3 main.py` oppure fare doppio click su `main.py`.

#### Funzione di aggiornamento
In fase di scaricamento delle videolezioni verrà chiesto all'utente se vuole mantenere aggiornate le videolezioni.
Per mantenerle aggiornate e non dover scaricare manualmente le nuove videolezioni sarà sufficiente lanciare `main.py`
con l'opzioni `-u`, cioè eseguire `$ ./main.py -u`. Il programma a questo punto controllerà le cartelle delle
videolezioni scaricate e le confronterà con quelle presento su internet. Scaricherà dunque quelle necessarie.

## Crediti
Grazie a [gius-italy](https://github.com/gius-italy) per lo script del login e del download!
