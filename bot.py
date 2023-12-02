from discord.utils import get
import discord
from discord.ext import commands
import yt_dlp 
from youtubesearchpython import VideosSearch
import os
import json
import random
from datetime import datetime
import asyncio
import webuntis
from icecream import ic

"""
Dokumentieren!!!

Command ideen: 
reboot: Neustart einbauen
skip bearbeiten
"""

intents = discord.Intents.all()
prefix = "!"
client = commands.Bot(command_prefix=prefix ,intents= intents)
OWNER_ID : int = 552929239490494474

class MusicClient(commands.Cog):
    def __init__(self, prefix : str) -> None:
        self.prefix : str = prefix
        self.debug : bool = True
        self.queue : list[dict[str]] = [] # [{"links":"","titel":""}]
        self.loopModeEnaled : bool = False
        self.randomModeEnabled : bool = False
        self.FFMPEG_OPTIONS = {'before_options':'-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5', 'options': '-vn'}
        ic("MusicClient geladen")
#                                                        ---normale Methoden---

    def getPlaylistJson(self):
        with open(f"{os.path.join(os.path.dirname(os.path.realpath(__file__)))}\\song.json", 'r') as file:
            data = file.read()
            data = json.loads(data)
            file.close()
        return data
    
    def setPlaylistJson(self, arg : dict):
        data : dict[list[dict[str,str]]] = self.getPlaylistJson()
        with open(f"{os.path.join(os.path.dirname(os.path.realpath(__file__)))}\\song.json", "w") as file:
            liste : list = data['songs']
            liste.append(arg)
            data['songs'] = liste
            json.dump(data, file, sort_keys= True, indent= 4)
            file.close()  

    def getLogJson(self):
        with open(f"{os.path.join(os.path.dirname(os.path.realpath(__file__)))}\\log.json", 'r') as file:
            data = file.read()
            data = json.loads(data)
            file.close()
        return data
    
    def setLogJson(self, arg : dict):
        data : dict[list[dict[str,str]]] = self.getPlaylistJson()
        with open(f"{os.path.join(os.path.dirname(os.path.realpath(__file__)))}\\log.json", "w") as file:
            logs : list[dict] = data.get('log')
            if logs != None: 
                logs.append({
                    "date": datetime.now(),
                    "log": arg
                })
            json.dump(data, file, sort_keys= True, indent= 4)
            file.close() 

    def setIdeaJson(self, arg : dict, author):
        data : dict[list[dict[str,str]]] = self.getLogJson()
        with open(f"{os.path.join(os.path.dirname(os.path.realpath(__file__)))}\\log.json", "w") as file:
            logs : list[dict] = data.get('Idea')
            if logs != None: 
                logs.append({
                    "author": author,
                    "Idea": arg,
                    "done": False
                })
            json.dump(data, file, sort_keys= True, indent= 4)
            file.close()

#                                                        ---async Methoden---

    async def next(self, ctx):#funktioniert
        """
        soll das nächste lied abspielen
        """
        try:
            if self.randomModeEnabled:
                i = random.randint(0 , len(self.queue) - 1)
                removedSong = self.queue.pop(i)
            
            else:
                removedSong = self.queue.pop(0)
            
            if self.debug:
                ic(f"removedSong: {removedSong}")
                ic(f"loop: {self.loopModeEnaled}")
            
            if self.loopModeEnaled:    
                # appends lastPlayed song to the end
                self.queue.append(removedSong)
                await self.player(ctx, self.queue[0])

            if self.queue != []:    
                await self.player(ctx, self.queue[0])

           
        except IndexError:
            ic("Queue ist leer")

    async def player(self, ctx, song : dict): # funktioniert
        """
        Spielt ein Lied: für weitere muss über play die loop aktiv sein
        der song parameter muss eine link sein!!!
        """

        voice_client = get(client.voice_clients, guild= ctx.guild)
        ydlOpts = {
            'outtmpl': '%(id)s.%(ext)s',
            'format': 'bestaudio'
            }
        
        try: 
            with yt_dlp.YoutubeDL(ydlOpts) as ydl:
                try:
                    if song.get("link") is None:
                        raise IndexError()
                    
                    if self.debug:
                        ic(f"{song.get("link")} \n {song.get("titel")}")

                    info : dict = ydl.extract_info(song.get("link"), download= False)
                    url = info.get('url')
                    voice = discord.FFmpegPCMAudio(url, **self.FFMPEG_OPTIONS)
                      
                    voice = discord.PCMVolumeTransformer(voice)
                    voice.volume = 1
                    voice_client.play(voice, after= lambda e: asyncio.run_coroutine_threadsafe(self.next(voice_client), client.loop).result())
                
                except IndexError:
                    ic("Beende Player da kein Lied vorhanden")

        except yt_dlp.utils.DownloadError:
            await self.next(ctx)

    async def skip_by_steps(self, ctx, steps): # funktioniert
        """
        Spult in der Liste vor, stopt das Lied und spielt das neue
        """
        # rückwärts skippen
        if steps < 0:
            # temporärer zwischenspeicher der Songs
            tempList : list = [] 

            #skips
            for _ in range(steps * -1):
                buffer = self.queue.pop(-1)
                tempList.append(buffer)

                #log auf shell
                if self.debug:
                    ic(buffer)
                    ic(tempList)

            for element in tempList:
                self.queue.insert(0, element)

            if self.debug:
                ic(f"Spiele nun: {self.queue[0]}")

            await self.stop(ctx)
            await self.player(ctx, self.queue[0])

        # vorwärts skippen
        elif len(self.queue) - 1 >= steps:
            for _ in range(steps):
                buffer = self.queue.pop(0)
                if self.loopModeEnaled:
                    self.queue.append(buffer)

            if self.debug:
                ic(f"Spiele nun: {self.queue[0]}")

            await self.stop(ctx)
            await self.player(ctx, self.queue[0])

        else: 
            await ctx.send("soweit kann ich nicht skippen, entweder geringe Zahl hinter `!skip` angeben oder playlist löschen lassen und mit play neu lieder hinzufügen")

#                                                        ---Events---

    @client.event
    async def on_ready():#funktioniert
        await client.add_cog(MusicClient(prefix))
        await client.add_cog(Fun())
        await client.change_presence(activity=discord.Activity(type=discord.ActivityType.playing, name=f"Mit sich selbst"))
        ic("Online")
        user = client.get_user(OWNER_ID)
        await user.send("Klar soweit!")

#                                                        ---Admin-Commands---

    @commands.command()
    async def skip(self, ctx):#funktioniert
        """
        Stoppt das Aktuelle Lied und spielt dann das nächste
        """

        # erhalt der Intruktionen: steps zum Vorspulen
        command : str = ctx.message.content
        newCommand : list = command.split(" ")
        buffer = newCommand.pop(0)    

        # Logging Debug auf Console 
        if self.debug:
            ic(command)
            ic(newCommand)
            ic(buffer)
        

        if newCommand == []:
            newCommand = 1
            if self.debug:
                ic(newCommand)
            await self.skip_by_steps(ctx, newCommand)
            
        else:
            newCommand = int(newCommand[0])
            if self.debug:
                ic(newCommand)
            await self.skip_by_steps(ctx, newCommand)

    @commands.command()#admin methode
    async def reboot(self, ctx):#Admin Rechte müssen noch Implementiert werden 
        """
        Funktioniert noch nicht einwandfrei - nur Warning
        Findet momentan nur sein eigenen Pfad

        Mögliche Lösung:
        den Skript Pfad des bots als Parameter übergeben, oder als config.json

        !!PRÜFEN
        ruft ein anderes Skript auf, das diesen Bot beendet und anschließend neustartet.
        """
        if client.get_user(OWNER_ID) != ctx.message.author:
            await ctx.send("Du bist nicht berechtigt diesen Command zunutzen da du nicht der Entwickler bist, hehehe!")
            return
        
        if self.debug:
            ic("Der Bot wird Heruntergefahren, Neustart in Arbeit!")

        await self.clearQueue(ctx)
        await self.stop(ctx)
        await self.leave(ctx)
        await ctx.send("Der Bot wird Heruntergefahren, Neustart in Arbeit!")
        await client.close()
        
    @commands.command()
    async def enabledebug(self, ctx):
        if ctx.message.author != client.get_user(OWNER_ID):
            if self.debug:
                ic(f"{ctx.message.author} tried using enable Deubg Mode!")

            await ctx.send("Command for Owner, not for you!")
            return

        self.debug = not self.debug
        ic(self.debug)

    @commands.command()
    async def getAllIdeas(self, ctx): # for admin
        data : dict = self.getLogJson()
        data = data.get('Idea')

        for element in data:
            if not element.get('done'):

                if self.debug:
                    ic(element.get("Idea"))

                await ctx.send(element.get('Idea'))

            if self.debug:
                ic("Der Entwickler hat erstmal Pause, keine neuen Ideen")

            await ctx.send("Der Entwickler hat erstmal Pause, keine neuen Ideen")

#                                                        ---Commands---

    @commands.command()
    async def shuffle(self, ctx):
        self.randomModeEnabled = not self.randomModeEnabled
        await ctx.send(f"Random Mode: {self.randomModeEnabled}")

    @commands.command()
    async def idee(self, ctx):
        """
        Gebe dein Wunsch an, der dir an diesem Bot fehlt. Dies wird versucht in diesem Bot zuverwirklichen!
        """
        message : str = ctx.message.content
        author : str = ctx.message.author
        newMessage = message.split(" ")
        newMessage.pop(0)
        idea = ""
        for element in newMessage:
            idea += element
            idea += " "

        self.setIdeaJson(arg= idea, author= str(author))
        if self.debug:
            ic(f"{idea} von {author} wurde abgespeichert, und wird demnächst bearbeitet")
        await ctx.send(f"{idea} von {author} wurde abgespeichert, und wird demnächst bearbeitet")

    @commands.command()
    async def clearQueue(self, ctx):#funktioniert
        """Leert die Queue"""
        self.queue.clear()
        if self.debug:
            ic(f"Die Queue ist geleert: {self.queue}")
        await ctx.send(f"Die Queue ist geleert: {self.queue}")

    @commands.command()
    async def cTitel(self, ctx):#funktioniert
        """Gibt die Title der Queue aus"""
        if self.queue == []:
            await ctx.send("Die Queue ist leer!")
            return
        
        if self.debug:
            ic(f"Queue: {self.queue[0].get("titel")}")
        await ctx.send(f"Queue: {self.queue[0].get("titel")}")

    
    @commands.command()
    async def cLink(self, ctx):#funktioniert
        """Gibt die Title der Queue aus"""
        if self.queue == []:
            await ctx.send("Die Queue ist leer!")
            return
        
        if self.debug:
            ic(f"Queue: {self.queue[0].get("link")}")
        await ctx.send(f"Queue: {self.queue[0].get("link")}")

    @commands.command()
    async def loop(self, ctx):#funktioniert
        """
        Aktiviert eine Endloss Schleife
        """
        self.loopModeEnaled = not self.loopModeEnaled
        if self.debug:
            ic(f"LoopMode: {self.loopModeEnaled}")
        if self.loopModeEnaled:
            await client.change_presence(activity=discord.Activity(type=discord.ActivityType.playing, name=f"In einer Schleife: {self.loopModeEnaled}"))
            await ctx.send("Loop enabled!")
        else: 
            await client.change_presence(activity=discord.Activity(type=discord.ActivityType.playing, name=f"In einer Schleife: {self.loopModeEnaled}"))
            await ctx.send("Loop disabled!")

    @commands.command()
    async def join(self, ctx): #funktioniert
        """
        Der Bot wird in den Channel mit dem Autor Connectet
        """
        if not ctx.message.author.voice:
            if self.debug:
                ic(f"{ctx.message.author.name} is not connected to a voice channel")
    
            await ctx.send(f"{ctx.message.author.name} is not connected to a voice channel")
        else:
            if self.debug:
                ic("Connecting")
            channel = ctx.message.author.voice.channel
            await channel.connect()

    @commands.command()
    async def leave(self, ctx):#funktioniert
        """
        Wenn der Bot in einem Channel ist, wird dieser disconnectet
        """
        if self.debug:
            ic("Trying to leave channel")
        if ctx.voice_client is None:
            return
        
        elif ctx.voice_client.is_connected():
            if self.debug:
                ic("leaving")

            await ctx.voice_client.disconnect()
        else:
            return
        
    @commands.command()
    async def playQ(self, ctx):#funktioniert
        """
        Spielt alle Songs ab, die bisher gesucht worden sind
        """
        try:
            if ctx.voice_client.is_connected():
                songs = self.getPlaylistJson()
                if self.debug:
                    ic("loading songs from jsonData")

                for element in songs['songs']:
                    self.queue.append({"link": element['link'], "titel": element['title']})
        
                if ctx.voice_client.is_playing():
                    return
                
                if self.queue != []:
                    await self.player(ctx, self.queue[0])
                
        except AttributeError as e:
            if self.debug:
                ic(e)
            return

    @commands.command()
    async def play(self, ctx):#funktioniert
        """
        Fügt das gesuchte Lied der Queue zu, spielt bei Gelegenheit ab
        """
        sentence : str = ctx.message.content
        
        newSentence = sentence.split(" ")
        newSentence.pop(0)
        song = ""
        for element in newSentence:
            song += " "
            song += element
        
        if self.debug:
            ic(song)

        if song == "":
            try:
                if self.queue != []:
                    await self.player(ctx, self.queue[0])

            except IndexError:
                #loggen
                if self.debug:
                    ic(f"Tut mir leid, es fehlt ein Lied und es war nichts in der Queue. Bitte gebe nach '{self.prefix}' den Titel des Liedes an oder einen Link!")
                await ctx.send(f"Tut mir leid, es fehlt ein Lied und es war nichts in der Queue. Bitte gebe nach '{self.prefix}' den Titel des Liedes an oder einen Link!")
            return
        
        videosSearch = VideosSearch(song, limit= 1)
        result : dict | str = videosSearch.result()

        self.queue.insert(0, {"link": result['result'][0]['link'], "titel": result['result'][0]['title']})

        data = self.getPlaylistJson()
        for element in data['songs']:
            if element['link'] == result['result'][0]['link']:       
                if self.debug: 
                    ic(f"Bei der Suche nach {song} wurde folgender Link \n gefunden {result['result'][0]['link']}, dieser wurde der Queue hinzugefügt")

                await ctx.send(f"Bei der Suche nach {song} wurde folgender Link \n gefunden {result['result'][0]['link']}, dieser wurde der Queue hinzugefügt")
                if ctx.voice_client.is_playing():
                    return
                
                if self.queue != []: # wenn die Queue nicht leer ist!
                    await self.player(ctx, self.queue[0]) 

                return
           
        songDict : dict = {
            "title": result['result'][0]['title'],
            "link": result['result'][0]['link']
        }
        self.setPlaylistJson(songDict)

        await ctx.send(f"Bei der Suche nach {song} wurde folgender Link \n gefunden {result['result'][0]['link']}, dieser wurde der Queue hinzugefügt")
        if ctx.voice_client.is_playing():
            return
        if self.queue != []:
            await self.player(ctx, self.queue[0])

        
    @commands.command()
    async def stop(self, ctx):#funktioniert
        """
        Stopt das Lied, wenn eins gespielt wird
        """
        if self.debug:
            ic("Stopping the current Song")

        if ctx.voice_client is None:
            return
        
        elif ctx.voice_client.is_connected():
            if ctx.voice_client.is_playing():
                await ctx.send("Das momentane Lied wird nun gestoppt!")
                ctx.voice_client.stop()
        return
        
    @commands.command()
    async def pause(self, ctx):#funktioniert
        """
        Pausiert das momentan gespielte Lied
        """
        if self.debug:
            ic("Pausing Song")

        if ctx.voice_client.is_playing:
            ctx.voice_client.pause()

            if self.debug:
                ic("pausiert")

            await ctx.send("pausiert")

        else:
            if self.debug:
                ic("Es wird im Moment kein Song gespielt!")

            await ctx.send("Es wird im Moment kein Song gespielt!")

    @commands.command()
    async def resume(self, ctx):#funktioniert
        """
        Gibt das momentan pausierte Lied wieder
        """
        if ctx.voice_client.is_paused():
            ctx.voice_client.resume()
        else:
            if self.debug:
                ic("Es wird im Moment kein Song pausiert!")
            await ctx.send("Es wird im Moment kein Song pausiert!")

    @commands.command()
    async def repeat(self, ctx):#funktioniert
        """
        Spielt das letzt gespielte Lied als nächstes ab
        """
        def putSongInFirst(songList : list, song : str):
            """Soll die Liste updaten um den Song, und diese zurückgeben"""
            newList = [song]
            for element in songList:
                newList.append(element)
            if self.debug:
                ic(f"Inside of repeat: putSongInFirst \n {newList}")
            return newList

        await ctx.send(f"{self.queue[0].get("titel")} wurde der Queue hinzugefügt \n einfach !skip in den Chat zum vorspulen")
        if ctx.voice_client.is_playing():
            if self.debug:
                ic(self.queue)
            self.queue = putSongInFirst(songList= self.queue, song= self.queue[0])

class Fun(commands.Cog):
    def __init__(self) -> None:
        ic("Spielburg geladen")

    def getSongJson(self):
        with open(f"{os.path.join(os.path.dirname(os.path.realpath(__file__)))}\\song.json", 'r') as file:
            data = file.read()
            data = json.loads(data)
            file.close()
        return data
    
    def setZitate(self, arg : dict):
        data : dict[list[dict[str,str]]] = self.getSongJson()
        with open(f"{os.path.join(os.path.dirname(os.path.realpath(__file__)))}\\song.json", "w") as file:
            liste : list = data['Zitate']
            liste.append(arg)
            data['Zitate'] = liste
            json.dump(data, file, sort_keys= True, indent= 4)
            file.close() 

    @commands.command()
    async def schreibe(self, ctx):
        """Schreibt die Nachricht zwischen Befehl und Id an die Id
        
        Es wird die Nachricht gespalten, danach die Id ausgelesen,
        Befehl und Id rausgekürzt und der Satz wieder aneinander gefügt mit
        Leerzeichen dazwischen, dies wird dann der Id zugesendet
        """
        msg = ctx.message.content
        messagelist : list = msg.split(" ")
        userId = messagelist[-1]
        messagelist.pop(0)
        messagelist.pop(-1)
        message = ""
        for element in messagelist:
            message += element+" "
        user = client.get_user(int(userId))
        await user.send(message)

    @commands.command()
    async def zitat(self, ctx):
        """Sendet ein Zitat"""
        data = self.getSongJson()
        zitate : list = data['Zitate']
        i = random.randint(0, len(zitate)-1)
        await ctx.send(zitate[i])

    @commands.command()
    async def appendZitat(self, ctx, zitat):
        """Fügt der Zitatenliste das neue Zitat hinzu"""
        self.setZitate(zitat)
        await ctx.send(f"Folgendes Zitat wurde der Liste hinzugefügt: {zitat}")

    @commands.command()
    async def zitatiere(self, ctx, userId : str):
        """Sendet der Id ein zufälliges Zitat zu"""
        data = self.getSongJson()
        zitate: list = data['Zitate']
        i = random.randint(0, len(zitate)-1)
        user = client.get_user(int(userId))
        await ctx.send(f"{zitate[i]} wurde gesendet an die Id: {userId}")
        await user.send(zitate[i])

#Projekt auf ICE
class Webuntis(commands.Cog):
    def __init__(self) -> None:
        """
        Soll alles was in der Schule gebraucht wird abfragen können.
        """
        self.s = webuntis.Session(
            server='terpsichore.webuntis.com',
            username='Michael.Grumann',
            password='Einbrecher65',
            school='RFGS-Freiburg',
            useragent='WebUntis Test'
        )
        ic("Webuntis geladen")

    @commands.command()
    async def freierRaum(self, ctx):
        data = self.s.rooms()
        """
        soll Freieräume anzeigen, außer spezielle Fachräume: wo Computer stehen
        """
        await ctx.send("soll Freieräume anzeigen, außer spezielle Fachräume: wo Computer stehen")    

if __name__ == '__main__':

    TOKEN = ""
    client.run(token=TOKEN)
