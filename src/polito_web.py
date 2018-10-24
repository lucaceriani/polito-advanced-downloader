import requests
import os
import re
import html
import getpass
import pickle
import time


class PolitoWeb:
    base_video_url = 'https://didattica.polito.it/portal/pls/portal/sviluppo.videolezioni.vis?cor='
    login_cookie = None
    min_deep = None
    max_deep = None
    dump_name = None
    dl_folder = None
    lista = {}  # da definire vuota, non None!!

    def set_max_deep(self, max_deep):
        self.max_deep = max_deep

    def set_dump_name(self, filename):
        self.dump_name = filename

    def set_interval(self, min_deep, max_deep):
        self.min_deep = min_deep
        self.max_deep = max_deep

    def set_dl_folder(self, dl_folder):
        if not os.path.isdir(dl_folder):
            os.mkdir(dl_folder)
        self.dl_folder = dl_folder

    # @return boolean
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
                #log.error("Credenziali errate! Utente: %s", user)
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
                #log.critical("Qualcosa nel login non ha funzionato!")
                return False
        # se sono arrivato qui vuol dire che sono loggato
        self.login_cookie = login_cookie
        return True

    def crawl(self):
        """
        In teoria la funzione crawl non dovrebbe neanche esistere: bisognerebbe acquisire
        i link delle videolezioni disponibili in maniera diversa, non tramite bruteforce.
        """

        if not self.__ready():
            return 0

        # controllo se esiste il file pickle di crawling...
        if os.path.isfile(self.dump_name):
            print("Lista caricata da file...")
            #log.info("Lista crawling caricata da: %s", self.dump_name)
            self.__carica_lista()
            return 0

        # altrimenti procedo con il crawling
        for i in range(self.min_deep, self.max_deep):
            page = self.__get_page(self.base_video_url + str(i))
            if page.startswith("Access denied"):
                continue

            materia = re.findall("<div class=\"h2 text-primary\">(.*)</div>", page)
            materia = (materia[0] if len(materia) > 0 else "")

            prof = re.findall("<h3>(.*)</h3>", page)
            prof = (prof[0] if len(prof) > 0 else "")

            anno = re.findall("<span class=\"small\">.*[0-9]{2}/[0-9]{2}/([0-9]{4})</span>", page)
            anno = (anno[0] if len(anno) > 0 else "")

            if len(materia) > 0:
                print("[" + str(i) + "] \"" + materia + "\" " + prof + " " + anno)
                self.__aggiungi_in_lista(i, materia, prof, anno)

        # salvo la Lista
        self.__salva_lista()

    def menu(self):
        materie_sorted = []
        i = 0
        for key, value in sorted(self.lista.items()):
            i += 1
            print("[%.3d] %s" % (i, key))
            materie_sorted.append(value)

        m = 0
        while not (1 <= m <= len(materie_sorted)):  # aspetto una materia valida
            m = int(input("Materia: "))

        i = 0
        nome = self.__get_mat_name_from_id(m - 1)
        for a in self.lista[nome]:  # stampo tutte le videolezioni di quella materia
            i += 1
            print(" [%.3d] %s - %s" % (i, a[1], a[2]))  # a[0]=codice a[1]=professore a[2]=anno

        n = 0
        while not (1 <= n <= i):
            n = int(input("Lezione: "))

        update = ""
        while not (update == "s" or update == "n"):
            update = input("Mantenere la materia aggiornata all'ultima videolezione? [s/n] ")
        update = (True if update == "s" else False)

        # se non c'è crea la cartella per ospitare la videolezione
        nome_cartella_corso = self.__generate_folder_name(nome, materie_sorted[m - 1][n - 1][0], update)
        if not os.path.isdir(os.path.join(self.dl_folder, nome_cartella_corso)):
            os.mkdir(os.path.join(self.dl_folder, nome_cartella_corso))
        # scarica le videolezioni

        self.__download_video(str(materie_sorted[m - 1][n - 1][0]), nome_cartella_corso)
        return 1

    # funzione che ricerca tutte le cartelle che hanno un numero tra parentesi
    # che sarebbe l'id del corso (nome della cartella specificato da __generateFolderName)
    # se le trova e ci sono nuove videolezioni procede a scaricarle
    def check_for_updates(self):
        for folderName in os.listdir(self.dl_folder):
            id_corso = re.search(".?\(([0-9]+)\)", folderName)
            if id_corso and not folderName.endswith("noupdate"):  # se la cartella è da aggiornare
                id_corso = id_corso.group(1)

                ultima = self.__find_last_video_number(folderName)  # ultima videolezione nella cartella
                links = self.__extract_video_links(id_corso)
                quante_videolezioni = len(links)  # numero di videolezioni online
                if quante_videolezioni == ultima:
                    continue  # mi fermo qui

                print("Ci sono " + str(quante_videolezioni - ultima) + " nuove videolezioni per " +
                      str(folderName.rsplit(' ', 1)[0]) + "!")
                lezioni_da_scaricare = [ultima + 1, quante_videolezioni]  # "range" delle videolezioni da scaricare
                self.__download_video(id_corso, folderName, lezioni_da_scaricare)

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
        return int(re.search(".?([0-9]+).?", ultimo_video).group(1))

    @staticmethod
    def __generate_folder_name(corso, codice, update):
        suffix = ("" if update else " - noupdate")
        return corso + " (" + str(codice) + ")" + suffix

    # @param inp = [start, end]
    def __download_video(self, id_corso, nome_cartella_corso, inp=None):
        print("Sto cercando le videolezioni...")
        links = self.__extract_video_links(id_corso)
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

    def __extract_video_links(self, id_corso):
        url = self.base_video_url + id_corso

        with requests.session() as s:
            s.cookies = self.login_cookie
            r = s.get(url)

            if "didattica.polito.it" in url:
                links = re.findall('href="(sviluppo\.videolezioni\.vis.*lez=\w*)">', r.text)
                for i in range(len(links)):
                    links[i] = 'https://didattica.polito.it/pls/portal30/' + html.unescape(links[i])
            elif "elearning.polito.it" in url:  # mantenuto per legacy
                links = re.findall("href='(template_video\.php\?[^']*)", r.text)
                for i in range(len(links)):
                    links[i] = 'https://elearning.polito.it/gadgets/video/' + html.unescape(links[i])
            else:
                print("Impossibile trovare le videolezioni")
                return 0
            return links

    def __get_mat_name_from_id(self, n):
        i = 0
        for key, value in sorted(self.lista.items()):
            if i == n:
                return key
            i += 1
        return None

    def __salva_lista(self):
        with open(self.dump_name, "wb") as f:
            pickle.dump(self.lista, f)

    def __carica_lista(self):
        with open(self.dump_name, "rb") as f:
            self.lista = pickle.load(f)

    def __aggiungi_in_lista(self, n, nome, prof, anno):
        if not (nome in self.lista):
            self.lista[nome] = []  # se non ci sono mai passato inizializzo la lista

        self.lista[nome].append([n, prof, anno])  # appendo le nuove info alla fine della lista

    def __ready(self):
        if (
                self.login_cookie is None or
                self.min_deep is None or
                self.max_deep is None or
                self.dump_name is None or
                self.dl_folder is None
        ):
            #log.critical("Sessione non pronta!")
            return 0
        else:
            return 1

    def __get_page(self, url):
        s = requests.session()
        s.cookies = self.login_cookie
        page = s.get(url, allow_redirects=False)
        return page.text if page else ""

    def __download_single_video(self, url, nome_cartella_corso):
        filename = url.split('/')[-1]
        print('Scaricando "' + filename + '"...')
        with requests.session() as s:
            f = s.get(url)
            open(os.path.join(*[self.dl_folder, nome_cartella_corso, filename]), 'wb').write(f.content)

    def __extract_download_url(self, url):
        with requests.session() as s:
            s.cookies = self.login_cookie
            r = s.get(url)
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
