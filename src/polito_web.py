import os
import re
import html
import time
import getpass
import requests
import urllib.parse
from bs4 import BeautifulSoup


class Link:
    codice = None
    anno = None
    is_elearn = False

    def __init__(self, code: str, year: str, is_elearn: bool):
        self.codice = code
        self.anno = year
        self.is_elearn = is_elearn

    def get_year(self):
        return self.anno

    def get_code(self):
        return self.codice

    def get_is_elearn(self):
        return self.is_elearn


class Corso:
    links = []
    nome = None
    periodo = None

    def __init__(self, nome: str, periodo: str):
        self.nome = nome
        self.periodo = periodo
        self.links = []

    def add_link(self, link):
        self.links.append(link)


class PolitoWeb:
    login_cookie = None
    dl_folder = None
    lista = []  # da definire vuota, non None!!

    def set_dl_folder(self, dl_folder):
        if not os.path.isdir(dl_folder):
            print("La cartella {} non esiste! La creo...".format(dl_folder));
            os.mkdir(dl_folder)
            print("Cartella {} creata!".format(dl_folder))
        self.dl_folder = dl_folder
        print("Cartella di download impostata: {}".format(dl_folder))

    def login(self, username=None, password=None):
        if (username is None) and (password is None):
            user = input("Username: ")
            passw = getpass.getpass("Password: ")
        else:
            user = username
            passw = password

        print("Logging in...")

        with requests.session() as s:
            s.get('https://idp.polito.it/idp/x509mixed-login')
            r = s.post('https://idp.polito.it/idp/Authn/X509Mixed/UserPasswordLogin',
                       data={'j_username': user, 'j_password': passw})
            rls = html.unescape(re.findall('name="RelayState".*value="(.*)"', r.text))
            if len(rls) > 0:
                relaystate = rls[0]
            else:
                # log.error("Credenziali errate! Utente: %s", user)
                return False
            samlresponse = html.unescape(re.findall('name="SAMLResponse".*value="(.*)"', r.text)[0])
            s.post('https://www.polito.it/Shibboleth.sso/SAML2/POST',
                   data={'RelayState': relaystate, 'SAMLResponse': samlresponse})
            r = s.post('https://login.didattica.polito.it/secure/ShibLogin.php')
            relaystate = html.unescape(re.findall('name="RelayState".*value="(.*)"', r.text)[0])
            samlresponse = html.unescape(re.findall('name="SAMLResponse".*value="(.*)"', r.text)[0])
            r = s.post('https://login.didattica.polito.it/Shibboleth.sso/SAML2/POST',
                       data={'RelayState': relaystate, 'SAMLResponse': samlresponse})
            if r.url == "https://didattica.polito.it/portal/page/portal/home/Studente":  # Login Successful
                login_cookie = s.cookies
            else:
                # log.critical("Qualcosa nel login non ha funzionato!")
                return False
        # se sono arrivato qui vuol dire che sono loggato
        self.login_cookie = login_cookie
        return True

    def crawl(self):
        """
        Questa funzione va a prendere le videolezioni dalla sezione materiale (primo/secondo/terzo anno)
        """
        with requests.session() as s:
            s.cookies = self.login_cookie
            # per arrivare a pagina_anni non specifico l'anno perché tanto mi serve solo i
            # link per primo/secondo/terzo anno
            pagina_anni = s.get("https://didattica.polito.it/portal/pls/portal/sviluppo.materiale.elenco?a=&t=E").text
            soup = BeautifulSoup(pagina_anni, "html.parser")
            tutti_gli_a = soup.find_all("a")

            periodo = 0
            nuovo_corso = None

            for a in tutti_gli_a:

                # encode e poi decode mi serve per renderla stringa e non StringSearchable (?) che mi
                # viene restituito da soup

                testo = str(a.contents[-1].encode("utf-8").decode("utf-8"))
                link = str(a.get("href").encode("utf-8").decode("utf-8"))
                is_elearn = False

                if a.get("onclick") is not None:
                    link = str(a.get("onclick").encode("utf-8").decode("utf-8"))
                    is_elearn = True

                # se trovo la parola anno nel link che sto considerando vuol dire che aumento l'anno in cui sono
                # se parto da 0: 1=primo anno, 2=secondo, 3=terzo, 4=magistrale
                if "anno" in testo or "Magistrale" in testo:
                    periodo += 1
                    continue

                titolo_corso = re.search("(.+ - .+) (\([0-9]+/[0-9]+\))", testo)
                anno_corso = re.search("\(([0-9]+/[0-9]+)\)", testo)
                codice_link = re.search("([0-9]+)", link)

                if titolo_corso and codice_link and anno_corso:
                    # pulisco il titolo del corso perché verrà usato come nome per una cartella quindi
                    # prendo solo i caratteri alfanumerici
                    titolo_corso = re.sub("'", "", titolo_corso.group(1))
                    titolo_corso = re.sub("[^\w \-()]", "_", titolo_corso)
                    anno_corso = anno_corso.group(1)
                    codice_link = codice_link.group(1)

                    nuovo_corso = Corso(titolo_corso, str(periodo))
                    nuovo_corso.add_link(Link(codice_link, anno_corso, is_elearn))
                    self.lista.append(nuovo_corso)

                # se trovo solo l'anno e non il titolo del corso aggiungo il link al nuovo_corso
                # che sarebbe il corso che sstavo considerando al passo precendete
                elif anno_corso and codice_link:
                    anno_corso = anno_corso.group(1)
                    codice_link = codice_link.group(1)
                    nuovo_corso.add_link(Link(codice_link, anno_corso, is_elearn))

        # for corso in self.lista:
        #    print(">>> " + corso.nome + " [" + corso.periodo + "]")
        #    for link in corso.links:
        #        print("\t" + link.anno + " - " + link.codice + (" @" if link.is_elearn else ""))

    def menu(self):

        periodo = 0

        print("[1] - Primo anno")
        print("[2] - Secondo anno")
        print("[3] - Terzo anno")
        print("[4] - Magistrale")

        while not 1 <= periodo <= 4:
            periodo = int(input("Scegli l'anno: "))

        # conversione a stringa per comodità
        periodo = str(periodo)

        # creo una lista dei corsi che l'utente seleziona per aiutarmi successivamente
        lista_corsi_selezionati = []
        for corso in self.lista:
            if corso.periodo == periodo:
                lista_corsi_selezionati.append(corso)
                print("[{:>2}] - {}".format(len(lista_corsi_selezionati), corso.nome))

        n_corso_scelto = 0
        while not 1 <= n_corso_scelto <= len(lista_corsi_selezionati):
            n_corso_scelto = int(input("Scegli il corso: "))

        # importante -1 perché sono indici di un vettore
        corso_scelto = lista_corsi_selezionati[n_corso_scelto - 1]
        print(corso_scelto.nome)

        for link in corso_scelto.links:
            print("[{}] - {}".format(corso_scelto.links.index(link) + 1, link.anno))

        n_link_scelto = 0
        while not 1 <= n_link_scelto <= len(corso_scelto.links):
            n_link_scelto = int(input("Scegli l'anno delle videolezioni: "))

        # importante il -1 come sopra...
        link_scelto = corso_scelto.links[n_link_scelto - 1]

        # chiedo all'utente se vuole mantenere aggiornate le videolezioni
        update = ""
        while not (update == "s" or update == "n"):
            update = input("Mantenere la materia aggiornata all'ultima videolezione? [s/n] ")
        update = (True if update == "s" else False)  # update diventa bool

        # se non c'è crea la cartella per ospitare la videolezione
        nome_cartella_corso = self.__generate_folder_name(corso_scelto, link_scelto, update)
        if not os.path.isdir(os.path.join(self.dl_folder, nome_cartella_corso)):
            os.mkdir(os.path.join(self.dl_folder, nome_cartella_corso))
        # scarica le videolezioni

        self.__download_video(link_scelto, nome_cartella_corso)
        return 1

    # funzione che ricerca tutte le cartelle che hanno un numero tra parentesi
    # che sarebbe l'id del corso (nome della cartella specificato da __generate_folder_name)
    # se le trova e ci sono nuove videolezioni procede a scaricarle
    def check_for_updates(self):
        for folder_name in os.listdir(self.dl_folder):
            if folder_name.endswith("noupdate"):
                continue

            link = self.__decode_folder_name(folder_name)
            # se non riesco a decodificare la cartella, continuo
            if link is None:
                continue

            if link is not None:
                ultima = int(self.__find_last_video_number(folder_name))  # ultima videolezione nella cartella
                links = self.__extract_video_links(link)
                quante_videolezioni = len(links)  # numero di videolezioni online
                if quante_videolezioni == ultima:
                    continue  # mi fermo qui

                print("Ci sono {} nuove videolezioni per {}!".format(quante_videolezioni - ultima,  folder_name))
                lezioni_da_scaricare = [ultima + 1, quante_videolezioni]  # "range" delle videolezioni da scaricare
                self.__download_video(link, folder_name, lezioni_da_scaricare)

    @staticmethod
    def bell():
        print(chr(7))
        time.sleep(1)

    # -------------- #
    # classi private #
    # -------------- #

    # trova il numero dell'ultima lezione scaricata nella cartella
    # @return integer
    def __find_last_video_number(self, cartella):
        cartella = os.path.join(self.dl_folder, cartella)
        ultimo_video = sorted(os.listdir(cartella))[-1]  # l'ultimo video in ordine alfabetico
        ultimo_numero = re.search(".?([0-9]+).?", ultimo_video)
        if ultimo_numero:
            return ultimo_numero.group(1)
        else:
            print("Non ho trovato nessun video. La cartella è forse vuota (?)")
            return 0

    def __generate_video_url(self, link: Link):
        base_url = "https://didattica.polito.it/portal/pls/portal/sviluppo.videolezioni.vis?cor="
        base_url_e = "https://elearning.polito.it/gadgets/video/template_video.php?"
        url = "<ERRORE NELLA GENERAZIONE URL>"
        if not link.is_elearn:
            url = base_url + link.codice
        else:
            with requests.session() as s:
                s.cookies = self.login_cookie
                data = s.get("https://didattica.polito.it/pls/portal30/sviluppo.materiale.json_dokeos_par?inc=" +
                             link.codice).json()
                url = base_url_e + urllib.parse.urlencode(data)
        # print(url)
        return url

    @staticmethod
    def __generate_folder_name(corso: Corso, link: Link, update):
        suffix = ("" if update else " - noupdate")
        codice = (link.codice if not link.is_elearn else "E_" + link.codice)
        return "{} ({}) [{}]{}".format(corso.nome, link.anno.replace("/", "-"), codice, suffix)

    @staticmethod
    def __decode_folder_name(folder_name: str):
        codice = re.search("\[([E_\d]+)\]", folder_name)
        anno = re.search("\((\d+-\d+)\)", folder_name)

        codice = codice.group(1) if codice else None
        anno = anno.group(1) if anno else None

        if codice is None:
            return None
        else:
            is_elearn = True if codice.startswith("E_") else False
            return Link(re.sub("E_", "", codice), anno, is_elearn)

    # @param inp = [start, end]
    def __download_video(self, link: Link, nome_cartella_corso, inp=None):
        print("Sto cercando le videolezioni...")
        links = self.__extract_video_links(link)
        quante_videolezioni = len(links)

        # mi serve passarlo come parametro dalla funzione checkForUpdates
        if inp is None:
            print(str(quante_videolezioni) + " videolezioni trovate!")
            print("Quali videolezioni vuoi scaricare? Inserisci un range o un numero...")
            print("(Per esempio per scaricarle tutte scrivi: 1-" + str(len(links)) + ")")
            inp = input("Lezioni: ").split("-")

        if len(inp) > 0:
            st = int(inp[0])
            end = (int(inp[1]) if len(inp) == 2 else int(inp[0]))
            for i in range(st, end + 1):
                url = self.__extract_download_url(links[i - 1])
                self.__download_single_video(url, nome_cartella_corso)
            print("--- Done! ---")
            self.bell()
        else:
            print("Riprova")

    def __extract_video_links(self, link: Link):
        url = self.__generate_video_url(link)

        with requests.session() as s:
            s.cookies = self.login_cookie
            r = s.get(url, verify=False)

            if "didattica.polito.it" in url:
                links = re.findall('href="(sviluppo\.videolezioni\.vis.*lez=\w*)">', r.text)
                for i in range(len(links)):
                    links[i] = 'https://didattica.polito.it/pls/portal30/' + html.unescape(links[i])
            elif "elearning.polito.it" in url:
                links = re.findall("href='(template_video\.php\?[^']*)", r.text)
                for i in range(len(links)):
                    links[i] = 'https://elearning.polito.it/gadgets/video/' + html.unescape(links[i])
            else:
                print("Impossibile trovare le videolezioni")
                return 0
            return links

    def __ready(self):
        if (
                self.login_cookie is None or
                self.dl_folder is None
        ):
            # log.critical("Sessione non pronta!")
            return 0
        else:
            return 1

    def __download_single_video(self, url, nome_cartella_corso):
        filename = url.split('/')[-1]
        print('Scaricando "' + filename + '"...')
        with requests.session() as s:
            f = s.get(url)
            open(os.path.join(*[self.dl_folder, nome_cartella_corso, filename]), 'wb').write(f.content)

    def __extract_download_url(self, url):
        with requests.session() as s:
            s.cookies = self.login_cookie
            r = s.get(url, verify=False)
            if "didattica.polito.it" in url:
                d_url = re.findall('href="(.*)".*Video', r.text)[0]
                r = s.get('https://didattica.polito.it' + html.unescape(d_url), allow_redirects=False)
                d_url = r.headers['location']
            elif "elearning.polito.it" in url:
                d_url = re.findall('href="(download.php[^\"]*).*video1', r.text)[0]
                r = s.get('https://elearning.polito.it/gadgets/video/' + html.unescape(d_url), allow_redirects=False)
                d_url = r.headers['location']
            else:
                print("Impossibile trovare i file da scaricare")
                d_url = None
                exit()
        return d_url
