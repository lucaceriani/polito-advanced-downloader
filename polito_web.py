import requests, os, urllib, re, html, getpass, pickle
import logging as log

log.basicConfig(level=100, filename='log.log', format='%(asctime)s - %(levelname)s: %(message)s')

class PolitoWeb:

    baseVideoUrl='https://didattica.polito.it/portal/pls/portal/sviluppo.videolezioni.vis?cor='
    loginCookie=None
    minDeep=None
    maxDeep=None
    dumpName=None
    dlFolder=None
    lista={} # da definire vuota, non None!!

    def __init__(self):
        log.debug("Creata sessione PolitoWeb")

    def setMaxDeep(self, maxDeep):
        self.maxDeep=maxDeep

    def setDumpName(self, filename):
        self.dumpName=filename

    def setInterval(self, minDeep, maxDeep):
        self.minDeep=minDeep
        self.maxDeep=maxDeep

    def setDlFolder(self, dlFolder):
        if not os.path.isdir(dlFolder): os.mkdir(dlFolder)
        self.dlFolder=dlFolder

    # @return boolean
    def login(self, username=None, password=None):
        if (username is None) and (password is None):
            user=input("Username: ")
            passw=getpass.getpass("Password: ")
        else:
            user=username
            passw=password

        print("Logging in...")

        with requests.session() as s:
            r=s.get('https://idp.polito.it/idp/x509mixed-login')
            r=s.post('https://idp.polito.it/idp/Authn/X509Mixed/UserPasswordLogin',data={'j_username':user,'j_password':passw})
            rls=html.unescape(re.findall('name="RelayState".*value="(.*)"',r.text))
            if len(rls)>0:
                relaystate=rls[0]
            else:
                log.error("Credenziali errate! Utente: %s", user)
                return False
            samlresponse=html.unescape(re.findall('name="SAMLResponse".*value="(.*)"',r.text)[0])
            r=s.post('https://www.polito.it/Shibboleth.sso/SAML2/POST',data={'RelayState':relaystate,'SAMLResponse':samlresponse})
            r=s.post('https://login.didattica.polito.it/secure/ShibLogin.php')
            relaystate=html.unescape(re.findall('name="RelayState".*value="(.*)"',r.text)[0])
            samlresponse=html.unescape(re.findall('name="SAMLResponse".*value="(.*)"',r.text)[0])
            r=s.post('https://login.didattica.polito.it/Shibboleth.sso/SAML2/POST',data={'RelayState':relaystate,'SAMLResponse':samlresponse})
            if r.url=="https://didattica.polito.it/portal/page/portal/home/Studente": #Login Successful
                login_cookie=s.cookies
            else:
                log.critical("Qualcosa nel login non ha funzionato!")
                return False
        # se sono arrivato qui vuol dire che sono loggato
        self.loginCookie=login_cookie
        return True

    def crawl(self):
        '''
        In teoria la funzione crawl non dovrebbe neanche esistere: bisognerebbe acquisire
        i link delle videolezioni disponibili in maniera diversa, non tramite bruteforce.
        '''

        if not self.__ready():
            return 0

        # controllo se esiste il file pickle di crawling...
        if (os.path.isfile(self.dumpName)):
            print("Lista caricata da file...")
            log.info("Lista crawling caricata da: %s", self.dumpName)
            self.__caricaLista()
            return 0

        # altrimenti procedo con il crawling
        for i in range(self.minDeep, self.maxDeep):
            page=self.__getPage(self.baseVideoUrl+str(i))
            if page.startswith("Access denied"): continue

            materia=re.findall("<div class=\"h2 text-primary\">(.*)<\/div>", page)
            materia = (materia[0] if len(materia)>0 else "")

            prof=re.findall("<h3>(.*)<\/h3>", page)
            prof = (prof[0] if len(prof)>0 else "")

            anno=re.findall("<span class=\"small\">.*[0-9]{2}\/[0-9]{2}\/([0-9]{4})<\/span>", page);
            anno = (anno[0] if len(anno)>0 else "")

            if len(materia)>0:
                print("["+str(i)+"] \""+materia+"\" "+prof+" "+anno)
                self.__aggiungiInLista(i, materia, prof, anno)

        #salvo la Lista
        self.__salvaLista()

    def menu(self):
        materie_sorted=[]
        i=0
        for key,value in sorted(self.lista.items()):
            i+=1
            print("[%.3d] %s" % (i, key))
            materie_sorted.append(value)

        m=0
        while not (m>=1 and m<=len(materie_sorted)): #aspetto una materia valida
            m=int(input("Materia: "))

        i=0
        nome=self.__getMatNameFromId(m-1)
        for a in self.lista[nome]: #stampo tutte le videolezioni di quella materia
            i+=1
            print(" [%.3d] %s - %s" % (i, a[1], a[2])) # a[0]=codice a[1]=professore a[2]=anno

        n=0
        while not (n>=1 and n<=i):
            n=int(input("Lezione: "))

        update = ""
        while not (update == "s" or update == "n"):
            update = input("Mantenere la materia aggiornata all'ultima videolezione? [s/n] ")
        update = (True if update == "s" else False)

        # se non c'è crea la cartella per ospitare la videolezione
        nomeCartellaCorso=self.__generateFolderName(nome, materie_sorted[m-1][n-1][0], update)
        if not os.path.isdir(os.path.join(self.dlFolder, nomeCartellaCorso)):
            os.mkdir(os.path.join(self.dlFolder, nomeCartellaCorso))
        # scarica le videolezioni

        self.__downloadVideo(str(materie_sorted[m-1][n-1][0]), nomeCartellaCorso)
        return 1

    # funzione che ricerca tutte le cartelle che hanno un numero tra parentesi
    # che sarebbe l'id del corso (nome della cartella specificato da __generateFolderName)
    # se le trova e ci sono nuove videolezioni procede a scaricarle
    def checkForUpdates(self):
        for folderName in os.listdir(self.dlFolder):
            idCorso = re.search(".?\(([0-9]+)\)", folderName)
            if idCorso and not folderName.endswith("noupdate"): # se la cartella è da aggiornare
                idCorso = idCorso.group(1)

                ultima = self.__findLastVideoNumber(folderName) # ultima videolezione nella cartella
                links=self.__extractVideoLinks(idCorso)
                quanteVideolezioni = len(links) # numero di videolezioni online
                if quanteVideolezioni == ultima:
                    continue # mi fermo qui

                print ("Ci sono " + str(quanteVideolezioni-ultima) + " nuove videolezioni per "+ folderName.rsplit(' ', 1)[0] + "!")
                lezioniDaScaricare = [ultima+1, quanteVideolezioni] # "range" delle videolezioni da scaricare
                self.__downloadVideo(idCorso, folderName, lezioniDaScaricare)

    def bell():
        print(chr(7))
    # -------------- #
    # classi private #
    # -------------- #

    # trova il numero dell'ultima lezione scaricata nella cartella
    # @return integer
    def __findLastVideoNumber(self, cartella):
        cartella = os.path.join(self.dlFolder, cartella)
        ultimoVideo = sorted(os.listdir(cartella))[-1] # l'ultimo video in ordine alfabetico
        return int(re.search(".?([0-9]+).?", ultimoVideo).group(1))


    def __generateFolderName(self, corso, codice, update):
        suffix = ("" if update else " - noupdate")
        return corso + " (" + str(codice) + ")" + suffix

    def __getCodeFromFolderName(self, folderName):
        return None

    # @param inp = [start, end]
    def __downloadVideo(self, idCorso, nomeCartellaCorso, inp=None):
        print("Sto cercando le videolezioni...")
        links=self.__extractVideoLinks(idCorso)
        quanteVideolezioni = len(links)

        # mi serve passarlo come parametro dalla funzione checkForUpdates
        if inp is None:
            print(str(quanteVideolezioni)+" videolezioni trovate!")
            print("Quali videolezioni vuoi scaricare? Inserisci un range o un numero...")
            print("(Per esempio per scaricarle tutte scrivi: 1-"+str(len(links))+")")
            inp=input("Lezioni: ").split("-")

        if len(inp)>0:
            st=int(inp[0])
            end=(int(inp[1]) if len(inp)==2 else int(inp[0]))
            for i in range(st,end+1):
                url=self.__extractDownloadUrl(links[i-1])
                self.__downloadSingleVideo(url, nomeCartellaCorso)
            print("--- Done! ---")
            self.bell()
        else:
            print("Riprova")

    def __extractVideoLinks(self, idCorso):
        url=self.baseVideoUrl+idCorso

        with requests.session() as s:
            s.cookies=self.loginCookie
            r=s.get(url)

            if "didattica.polito.it" in url:
                links=re.findall('href="(sviluppo\.videolezioni\.vis.*lez=\w*)">',r.text)
                for i in range(len(links)):
                    links[i]='https://didattica.polito.it/pls/portal30/'+html.unescape(links[i])
            elif "elearning.polito.it" in url: # mantenuto per legacy
                links=re.findall("href='(template_video\.php\?[^']*)",r.text)
                for i in range(len(links)):
                    links[i]='https://elearning.polito.it/gadgets/video/'+html.unescape(links[i])
            else:
                print("Impossibile trovare le videolezioni")
                return 0
            return links

    def __getMatNameFromId(self, n):
        i=0
        for key,value in sorted(self.lista.items()):
            if (i==n): return key
            i+=1
        return None

    def __salvaLista(self):
        with open(self.dumpName, "wb") as f:
            pickle.dump(self.lista, f)

    def __caricaLista(self):
        with open(self.dumpName, "rb") as f:
            self.lista=pickle.load(f)

    def __aggiungiInLista(self, n, nome, prof, anno):
        if not (nome in self.lista):
            self.lista[nome]=[] # se non ci sono mai passato inizializzo la lista

        self.lista[nome].append([n,prof,anno]) # appendo le nuove info alla fine della lista

    def __ready(self):
        if (self.loginCookie==None or self.minDeep==None or self.maxDeep==None or self.dumpName==None or self.dlFolder==None):
            log.critical("Sessione non pronta!")
            return 0
        else:
            return 1

    def __getPage(self, url):
        s=requests.session()
        s.cookies=self.loginCookie
        page=s.get(url, allow_redirects=False)
        return (page.text if page else "")

    def __downloadSingleVideo(self, url, nomeCartellaCorso):
        filename=url.split('/')[-1]
        print('Scaricando "'+filename+'"...')
        urllib.request.urlretrieve(url,os.path.join(*[self.dlFolder,nomeCartellaCorso,filename]))


    def __extractDownloadUrl(self, url):
        with requests.session() as s:
            s.cookies=self.loginCookie
            r=s.get(url)
            if "didattica.polito.it" in url:
                d_url=re.findall('href="(.*)".*Video',r.text)[0]
                r=s.get('https://didattica.polito.it'+html.unescape(d_url),allow_redirects=False)
                d_url=r.headers['location']
            elif "elearning.polito.it" in url:
                d_url=re.findall('href="(download.php[^\"]*).*video1',r.text)[0]
                r=s.get('https://elearning.polito.it/gadgets/video/'+html.unescape(d_url),allow_redirects=False)
                d_url=r.headers['location']
            else:
                print("Impossibile trovare i file da scaricare")
                exit()
        return d_url
