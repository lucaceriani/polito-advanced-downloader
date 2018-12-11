import argparse
import json
import os

from polito_web import PolitoWeb


def clear():
    os.system('cls' if os.name == 'nt' else 'clear')


def esci(x):
    input()
    exit(x)


if __name__ == "__main__":
    # command parser
    parser = argparse.ArgumentParser(description="Script Python per scaricare e tenere aggiornate le videolezioni\ndel \
    Politecnico di Torino.", add_help=True)
    parser.add_argument("-u", "--update-only", action="store_true", default=False,
                        help="Aggiorna le videolezioni ed esce")
    args = parser.parse_args()
    # end command parser

    print("PoliTo Advanced Downloader - v 0.3.0")

    settings = None
    try:
        with open("settings.json") as f:
            settings = json.load(f)
    except:
        print("Impossibile aprire il file di configurazione (settings.json)! Verificare di averlo rinominato"+
              "correttamente e di aver rispettato la sintassi.")
        esci(1)

    sess = PolitoWeb()
    sess.set_dl_folder(settings['download_folder'])

    if settings['credentials']['enabled']:
        if not sess.login(settings['credentials']['username'], settings['credentials']['password']):
            print("Impossibile effetture il login con le credenziali impostate in settings.json")
            esci(1)
    else:
        print("Acesso automatico disabilitato...")
        print("Credenziali di accesso per http://didattica.polito.it")
        while not sess.login():
            print("Impossibile effettuare il login, riprovare!")

    if args.update_only:  # se dovevo solo cercare gli aggiornamenti mi fermo qui
        sess.check_for_updates()
        sess.bell()
        exit(0)

    sess.crawl()
    while sess.menu():
        clear()


