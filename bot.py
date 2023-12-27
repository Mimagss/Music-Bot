from discord.utils import get
import discord
from discord import app_commands
from discord.ext import commands
from discord.ext.commands import has_permissions
import yt_dlp
from youtubesearchpython import VideosSearch
import os
import json
import random
from datetime import datetime
import asyncio
import webuntis
from icecream import ic

ic.configureOutput(prefix="Debug:", includeContext=True)
"""
Dokumentieren!!!

Command ideen: 
reboot: Neustart einbauen
skip bearbeiten

slash Commands:
msg senden: await interaction.response.send_message("hello", ephemeral= True)
decorator for slash commands: @app_commands.command()

await interaction.response.defer()
ctx = await commands.Context.from_interaction(interaction)
"""


def getsettings() -> dict:
    """Gibt alle Settings zurück"""
    with open(
        f"{os.path.join(os.path.dirname(os.path.realpath(__file__)))}/settings.json",
        "r",
    ) as file:
        data = file.read()
        data = json.loads(data)
        file.close()
    return data


settings: dict = getsettings()
bot_settings: dict = settings.get("settings_bot")
intents = discord.Intents.all()
prefix = bot_settings.get("prefix")
client = commands.Bot(command_prefix=prefix, intents=intents)
OWNER_ID: int = bot_settings.get("ownerId")

#                                                        ---Events---


@client.event
async def on_ready():  # funktioniert
    # init Bot
    debugMode = True  # Logs every Variable in commands on shell
    await client.add_cog(Client_Slash_Commands(prefix, debug=debugMode))
    await client.add_cog(Client_Prefix_Commands(prefix, debug=debugMode))
    await client.add_cog(Fun_Slash_Commands(debug=debugMode))
    await client.add_cog(Fun_Prefix_Commands(debug=debugMode))
    await client.add_cog(
        Webuntis_Slash_Commands(
            debug=debugMode, settings=settings.get("settings_Webuntis")
        )
    )
    await client.add_cog(
        Webuntis_Prefix_Commands(
            debug=debugMode, settings=settings.get("settings_Webuntis")
        )
    )
    await client.change_presence(
        activity=discord.Activity(
            type=discord.ActivityType.playing, name=f"Mit sich selbst"
        )
    )
    ic("Online")
    await client.tree.sync()
    user = client.get_user(OWNER_ID)
    await user.send("Klar soweit!")


#                                                        ---Class---


class MusicClient(commands.Cog):
    def __init__(self, prefix: str, debug: bool) -> None:
        self.prefix: str = prefix
        self.debug: bool = debug
        self.queue: list[dict[str]] = []  # [{"links":"","titel":""}]
        self.loopModeEnaled: bool = False
        self.randomModeEnabled: bool = False
        self.FFMPEG_OPTIONS = {
            "before_options": "-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5",
            "options": "-vn",
        }
        ic("MusicClient geladen")

    #                                                        ---normale Methoden---

    def getPlaylistJson(self):
        with open(
            f"{os.path.join(os.path.dirname(os.path.realpath(__file__)))}/song.json",
            "r",
        ) as file:
            data = file.read()
            data = json.loads(data)
            file.close()
        return data

    def setPlaylistJson(self, arg: dict):
        data: dict[list[dict[str, str]]] = self.getPlaylistJson()
        with open(
            f"{os.path.join(os.path.dirname(os.path.realpath(__file__)))}/song.json",
            "w",
        ) as file:
            liste: list = data["songs"]
            liste.append(arg)
            data["songs"] = liste
            json.dump(data, file, sort_keys=True, indent=4)
            file.close()

    def getLogJson(self):
        with open(
            f"{os.path.join(os.path.dirname(os.path.realpath(__file__)))}/log.json",
            "r",
        ) as file:
            data = file.read()
            data = json.loads(data)
            file.close()
        return data

    def setLogJson(self, arg: dict):
        data: dict[list[dict[str, str]]] = self.getPlaylistJson()
        with open(
            f"{os.path.join(os.path.dirname(os.path.realpath(__file__)))}/log.json",
            "w",
        ) as file:
            logs: list[dict] = data.get("log")
            if logs != None:
                logs.append({"date": datetime.now(), "log": arg})
            json.dump(data, file, sort_keys=True, indent=4)
            file.close()

    def setIdeaJson(self, arg: dict, author):
        data: dict[list[dict[str, str]]] = self.getLogJson()
        with open(
            f"{os.path.join(os.path.dirname(os.path.realpath(__file__)))}/log.json",
            "w",
        ) as file:
            logs: list[dict] = data.get("Idea")
            if logs != None:
                logs.append({"author": author, "Idea": arg, "done": False})
            json.dump(data, file, sort_keys=True, indent=4)
            file.close()

    #                                                        ---async Methoden---

    async def next(self, ctx: commands.Context):  # funktioniert
        """
        soll das nächste lied abspielen
        """
        try:
            # random choose of the song
            if self.randomModeEnabled:
                # TODO removed song should be played
                i = random.randint(0, len(self.queue) - 1)
                removedSong = self.queue.pop(i)

            else:
                removedSong = self.queue.pop(0)

            # log on console
            if self.debug:
                ic(f"removedSong: {removedSong}")
                ic(f"loop: {self.loopModeEnaled}")

            # starting player in loopmode
            if self.loopModeEnaled:
                # appends lastPlayed song to the end
                self.queue.append(removedSong)
                await self.player(ctx, self.queue[0])

            # starting normal player
            if self.queue != []:
                await self.player(ctx, self.queue[0])

        except IndexError:
            ic("Queue ist leer")

    async def player(self, ctx: commands.Context, song: dict):  # funktioniert
        """
        Spielt ein Lied: für weitere muss über play die loop aktiv sein
        der song parameter muss eine link sein!!!
        """

        voice_client = get(client.voice_clients, guild=ctx.guild)
        if voice_client is None:
            await ctx.send("Bot is not connected")
            return

        ydlOpts = {"outtmpl": "%(id)s.%(ext)s", "format": "bestaudio"}

        try:
            with yt_dlp.YoutubeDL(ydlOpts) as ydl:
                try:
                    # checking if there is any song
                    if song.get("link") is None:
                        raise IndexError()

                    # log on console
                    if self.debug:
                        ic(f"{song.get('link')} \n {song.get('titel')}")

                    # getting stream
                    info: dict = ydl.extract_info(song.get("link"), download=False)
                    url = info.get("url")

                    # preparing voice and plays it then
                    voice = discord.FFmpegPCMAudio(url, **self.FFMPEG_OPTIONS)
                    voice = discord.PCMVolumeTransformer(voice)
                    voice.volume = 1
                    voice_client.play(
                        voice,
                        after=lambda e: asyncio.run_coroutine_threadsafe(
                            self.next(voice_client), client.loop
                        ).result(),
                    )

                # ending player
                except IndexError:
                    ic("Beende Player da kein Lied vorhanden")

        # when a video isnt availible anymore
        except yt_dlp.utils.DownloadError:
            await self.next(ctx)

    async def skip_by_steps(self, ctx: commands.Context, steps):  # funktioniert
        """
        Spult in der Liste vor, stopt das Lied und spielt das neue
        """
        # rückwärts skippen
        if steps < 0:
            # temporärer zwischenspeicher der Songs
            tempList: list = []

            # skips
            for _ in range(steps * -1):
                buffer = self.queue.pop(-1)
                tempList.append(buffer)

                # log auf shell
                if self.debug:
                    ic(buffer)
                    ic(tempList)

            # resets queue
            for element in tempList:
                self.queue.insert(0, element)

            # log auf shell
            if self.debug:
                ic(f"Spiele nun: {self.queue[0]}")

            await self.stop(ctx)
            await self.player(ctx, self.queue[0])

        # checking possibility to skip
        elif len(self.queue) - 1 >= steps:
            # skips
            for _ in range(steps):
                buffer = self.queue.pop(0)
                # reappends removed song to queue for loop
                if self.loopModeEnaled:
                    self.queue.append(buffer)

            # log auf shell
            if self.debug:
                ic(f"Spiele nun: {self.queue[0]}")

            # reinit player
            await self.stop(ctx)
            await self.player(ctx, self.queue[0])

        else:
            await ctx.send(
                "soweit kann ich nicht skippen, entweder geringe Zahl hinter `!skip` angeben oder playlist löschen lassen und mit play neu lieder hinzufügen"
            )

    async def ping_hello(self, ctx: commands.Context):
        ic("hello")
        await ctx.send("hello world")

    async def skip(
        self, ctx: commands.Context, steps: int | None = None
    ):  # funktioniert
        """
        Stoppt das Aktuelle Lied und spielt dann das nächste
        """
        # erhalt der Intruktionen: steps zum Vorspulen
        if steps is None:
            steps = 1

            # log auf shell
            if self.debug:
                ic(steps)
            await self.skip_by_steps(ctx, steps)
            return

        # log auf shell
        if self.debug:
            ic(steps)
        await self.skip_by_steps(ctx, steps)

    async def reboot(self, ctx: commands.Context):
        # checks permissions
        if client.get_user(OWNER_ID) != ctx.message.author:
            await ctx.send(
                "Du bist nicht berechtigt diesen Command zunutzen da du nicht der Entwickler bist, hehehe!"
            )
            return

        # log auf shell
        if self.debug:
            ic("Der Bot wird Heruntergefahren, Neustart in Arbeit!")

        # clean reboot
        await self.clear_queue(ctx)
        await self.stop(ctx)
        await self.leave(ctx)
        await ctx.send("Der Bot wird Heruntergefahren, Neustart in Arbeit!")
        await client.close()

    async def enable_debug(self, ctx: commands.Context):
        """
        ONLY FOR BOT OWNER:
        Logs Information on console
        """
        if ctx.message.author != client.get_user(OWNER_ID):
            if self.debug:
                ic(f"{ctx.message.author} tried using enable Deubg Mode!")

            await ctx.send("Command for Owner, not for you!")
            return

        self.debug = not self.debug
        await ctx.send(f"Debugmode: {self.debug}")
        ic(self.debug)

    async def get_all_ideas(self, ctx: commands.Context):  # for admin
        """
        ONLY FOR BOT OWNER:
        Logs Ideas from other people on console
        """
        data: dict = self.getLogJson()
        data = data.get("Idea")

        for element in data:
            if not element.get("done"):
                ic(element.get("Idea"))

            if self.debug:
                ic("Der Entwickler hat erstmal Pause, keine neuen Ideen")

        await ctx.send("Ideas on log")

    async def shuffle(self, ctx: commands.Context):
        """
        Enables randommode
        """
        self.randomModeEnabled = not self.randomModeEnabled
        await ctx.send(f"Random Mode: {self.randomModeEnabled}")

    async def idee(self, ctx: commands.Context, idee: str):
        """
        Gebe dein Wunsch an, der dir an diesem Bot fehlt. Dies wird versucht in diesem Bot zuverwirklichen!
        """
        author: str = ctx.message.author

        self.setIdeaJson(arg=idee, author=str(author))
        if self.debug:
            ic(
                f"{idee} von {author} wurde abgespeichert, und wird demnächst bearbeitet"
            )
        await ctx.send(
            f"{idee} von {author} wurde abgespeichert, und wird demnächst bearbeitet"
        )

    async def clear_queue(self, ctx: commands.Context):  # funktioniert
        """Leert die Queue"""
        self.queue.clear()
        if self.debug:
            ic(f"Die Queue ist geleert: {self.queue}")
        await ctx.send(f"Die Queue ist geleert: {self.queue}")

    async def send_title(self, ctx: commands.Context):  # funktioniert
        """Gibt die Title der Queue aus"""
        # wenn queue leer
        if self.queue == []:
            await ctx.send("Die Queue ist leer!")
            return

        if self.debug:
            ic(f"Queue: {self.queue[0].get('titel')}")
        await ctx.send(f"Queue: {self.queue[0].get('titel')}")

    async def send_link(self, ctx: commands.Context):  # funktioniert
        """Gibt die Title der Queue aus"""
        # wenn queue leer
        if self.queue == []:
            await ctx.send("Die Queue ist leer!")
            return

        if self.debug:
            ic(f"Queue: {self.queue[0].get('link')}")
        await ctx.send(f"Queue: {self.queue[0].get('link')}")

    async def loop(self, ctx: commands.Context):
        # changes loopmodestate
        self.loopModeEnaled = not self.loopModeEnaled

        # log auf shell
        if self.debug:
            ic(f"LoopMode: {self.loopModeEnaled}")

        # gives out info about loopstate
        if self.loopModeEnaled:
            await client.change_presence(
                activity=discord.Activity(
                    type=discord.ActivityType.playing,
                    name=f"In einer Schleife: {self.loopModeEnaled}",
                )
            )
            await ctx.send("Loop enabled!")
        else:
            await client.change_presence(
                activity=discord.Activity(
                    type=discord.ActivityType.playing,
                    name=f"In einer Schleife: {self.loopModeEnaled}",
                )
            )
            await ctx.send("Loop disabled!")

    async def join(self, ctx: commands.Context):  # funktioniert
        """
        Der Bot wird in den Channel mit dem Autor Connectet
        """
        if not ctx.message.author.voice:
            if self.debug:
                ic(f"{ctx.message.author.name} is not connected to a voice channel")

            await ctx.send(
                f"{ctx.message.author.name} is not connected to a voice channel"
            )
        else:
            if self.debug:
                ic("Connecting")
            channel = ctx.message.author.voice.channel
            await ctx.send("connecting")
            await channel.connect()

    async def leave(self, ctx: commands.Context):  # funktioniert
        """
        Wenn der Bot in einem Channel ist, wird dieser disconnectet
        """
        if self.debug:
            ic("Trying to leave channel")
        if ctx.voice_client is None:
            await ctx.send("No connection to a voicechannel")
            return

        elif ctx.voice_client.is_connected():
            if self.debug:
                ic("leaving")
            await ctx.send("leaving")
            await ctx.voice_client.disconnect()
        else:
            return

    async def play_queue(self, ctx: commands.Context):  # funktioniert
        """
        Spielt alle Songs ab, die bisher gesucht worden sind
        """
        try:
            await ctx.send("Playing from a stored queue")
            if ctx.voice_client.is_connected():
                songs = self.getPlaylistJson()
                if self.debug:
                    ic("loading songs from jsonData")

                for element in songs["songs"]:
                    self.queue.append(
                        {"link": element["link"], "titel": element["title"]}
                    )

                if ctx.voice_client.is_playing():
                    return

                if self.queue != []:
                    await self.player(ctx, self.queue[0])

        except AttributeError as e:
            if self.debug:
                ic(e)
            return

    async def play(self, ctx: commands.Context, song: str):  # funktioniert
        """
        Fügt das gesuchte Lied der Queue zu, spielt bei Gelegenheit ab
        """
        if self.debug:
            ic(song)

        if song == "":
            try:
                if self.queue != []:
                    await self.player(ctx, self.queue[0])

            except IndexError:
                # loggen
                if self.debug:
                    ic(
                        f"Tut mir leid, es fehlt ein Lied und es war nichts in der Queue. Bitte gebe nach '{self.prefix}' den Titel des Liedes an oder einen Link!"
                    )
                await ctx.send(
                    f"Tut mir leid, es fehlt ein Lied und es war nichts in der Queue. Bitte gebe nach '{self.prefix}' den Titel des Liedes an oder einen Link!"
                )
            return

        videosSearch = VideosSearch(song, limit=1)
        result: dict | str = videosSearch.result()

        self.queue.insert(
            0,
            {
                "link": result["result"][0]["link"],
                "titel": result["result"][0]["title"],
            },
        )

        data = self.getPlaylistJson()
        for element in data["songs"]:
            if element["link"] == result["result"][0]["link"]:
                if self.debug:
                    ic(
                        f"Bei der Suche nach {song} wurde folgender Link \n gefunden {result['result'][0]['link']}, dieser wurde der Queue hinzugefügt"
                    )

                await ctx.send(
                    f"Bei der Suche nach {song} wurde folgender Link \n gefunden {result['result'][0]['link']}, dieser wurde der Queue hinzugefügt"
                )
                if ctx.voice_client is not None:
                    if ctx.voice_client.is_playing():
                        return

                if self.queue != []:  # wenn die Queue nicht leer ist!
                    await self.player(ctx, self.queue[0])

                return

        songDict: dict = {
            "title": result["result"][0]["title"],
            "link": result["result"][0]["link"],
        }
        self.setPlaylistJson(songDict)

        await ctx.send(
            f"Bei der Suche nach {song} wurde folgender Link \n gefunden {result['result'][0]['link']}, dieser wurde der Queue hinzugefügt"
        )
        if ctx.voice_client.is_playing():
            return
        if self.queue != []:
            await self.player(ctx, self.queue[0])

    async def stop(self, ctx: commands.Context):  # funktioniert
        """
        Stopt das Lied, wenn eins gespielt wird
        """
        if self.debug:
            ic("Stopping the current Song")
            await ctx.send("Stopping the current Song")

        if ctx.voice_client is None:
            return

        elif ctx.voice_client.is_connected():
            if ctx.voice_client.is_playing():
                await ctx.send("Das momentane Lied wird nun gestoppt!")
                ctx.voice_client.stop()
        return

    async def pause(self, ctx: commands.Context):  # funktioniert
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

    async def resume(self, ctx: commands.Context):  # funktioniert
        """
        Gibt das momentan pausierte Lied wieder
        """
        if ctx.voice_client.is_paused():
            await ctx.send("resume")
            ctx.voice_client.resume()
        else:
            if self.debug:
                ic("Es wird im Moment kein Song pausiert!")
            await ctx.send("Es wird im Moment kein Song pausiert!")

    async def repeat(self, ctx: commands.Context):
        def putSongInFirst(songList: list, song: str):
            """Soll die Liste updaten um den Song, und diese zurückgeben"""
            newList = [song]
            for element in songList:
                newList.append(element)
            if self.debug:
                ic(f"Inside of repeat: putSongInFirst \n {newList}")
            return newList

        await ctx.send(
            f"{self.queue[0].get('titel')} wurde der Queue hinzugefügt \n einfach !skip in den Chat zum vorspulen"
        )
        if ctx.voice_client.is_playing():
            if self.debug:
                ic(self.queue)
            self.queue = putSongInFirst(songList=self.queue, song=self.queue[0])


class InviteButtons(discord.ui.View):
    def __init__(self, inv: str):
        super().__init__()
        self.inv = inv

    @discord.ui.button(label="Invite Btn", style=discord.ButtonStyle.blurple)
    async def inviteBtn(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        await interaction.response.send_message(self.inv, ephemeral=True)


class Client_Slash_Commands(commands.Cog):
    def __init__(self, prefix: str, debug: bool):
        self.musicClient: MusicClient = MusicClient(prefix=prefix, debug=debug)

    #                                                        ---Admin-Commands---

    @app_commands.command()
    async def invite(self, interaction: discord.Interaction):
        await interaction.response.defer()
        ctx = await commands.Context.from_interaction(interaction)
        inv = await ctx.channel.create_invite()
        await ctx.send("Click below to invite someone", view=InviteButtons(str(inv)))

    @app_commands.command()
    async def ping_hello(self, interaction: discord.Interaction):
        await interaction.response.defer()
        ctx = await commands.Context.from_interaction(interaction)
        await self.musicClient.ping_hello(ctx=ctx)

    @app_commands.command()
    @app_commands.describe(steps="Wie viele Lieder möchtest du skippen")
    async def skip(
        self, interaction: discord.Interaction, steps: int | None = None
    ):  # funktioniert
        """
        Stoppt das Aktuelle Lied und spielt dann das nächste
        """
        await interaction.response.defer()
        ctx = await commands.Context.from_interaction(interaction)
        await ctx.send(f"Skipping queue: {steps}")
        await self.musicClient.skip_by_steps(ctx, steps)

    @app_commands.command()  # admin methode
    @has_permissions()
    # has permission
    async def reboot(
        self, interaction: discord.Interaction
    ):  # Admin Rechte müssen noch Implementiert werden
        """
        Funktioniert noch nicht einwandfrei - nur Warning
        Findet momentan nur sein eigenen Pfad

        Mögliche Lösung:
        den Skript Pfad des bots als Parameter übergeben, oder als config.json

        !!PRÜFEN
        ruft ein anderes Skript auf, das diesen Bot beendet und anschließend neustartet.
        """
        await interaction.response.defer()
        ctx = await commands.Context.from_interaction(interaction)
        await self.musicClient.reboot(ctx=ctx)

    @app_commands.command()
    @has_permissions()
    async def enable_debug(self, interaction: discord.Interaction):
        """
        ONLY FOR BOT OWNER:
        Logs Information on console
        """
        await interaction.response.defer()
        ctx = await commands.Context.from_interaction(interaction)
        await self.musicClient.enable_debug(ctx=ctx)

    @app_commands.command()  # has permission
    @has_permissions()
    async def get_all_ideas(self, interaction: discord.Interaction):  # for admin
        """
        ONLY FOR BOT OWNER:
        Logs Ideas from other people on console
        """
        await interaction.response.defer()
        ctx = await commands.Context.from_interaction(interaction)
        await self.musicClient.get_all_ideas(ctx=ctx)

    #                                                        ---Commands---

    @app_commands.command()
    async def shuffle(self, interaction: discord.Interaction):
        """
        Enables randommode
        """
        await interaction.response.defer()
        ctx = await commands.Context.from_interaction(interaction)
        await self.musicClient.shuffle(ctx=ctx)

    @app_commands.command()
    @app_commands.describe(idee="Deine Idee")
    async def idee(self, interaction: discord.Interaction, idee: str):
        """
        Gebe dein Wunsch an, der dir an diesem Bot fehlt. Dies wird versucht in diesem Bot zuverwirklichen!
        """
        await interaction.response.defer()
        ctx = await commands.Context.from_interaction(interaction)
        await self.musicClient.idee(ctx=ctx, idee=idee)

    @app_commands.command()
    async def clear_queue(self, interaction: discord.Interaction):  # funktioniert
        """Leert die Queue"""
        await interaction.response.defer()
        ctx = await commands.Context.from_interaction(interaction)
        await self.musicClient.clear_queue(ctx=ctx)

    @app_commands.command()
    async def send_title(self, interaction: discord.Interaction):  # funktioniert
        """Gibt die Title der Queue aus"""
        await interaction.response.defer()
        ctx = await commands.Context.from_interaction(interaction)
        await self.musicClient.send_title(ctx=ctx)

    @app_commands.command()
    async def send_link(self, interaction: discord.Interaction):  # funktioniert
        """Gibt die Title der Queue aus"""
        await interaction.response.defer()
        ctx = await commands.Context.from_interaction(interaction)
        await self.musicClient.send_link(ctx=ctx)

    @app_commands.command()
    async def loop(self, interaction: discord.Interaction):  # funktioniert
        """
        Aktiviert eine Endloss Schleife
        """
        await interaction.response.defer()
        ctx = await commands.Context.from_interaction(interaction)
        await self.musicClient.loop(ctx=ctx)

    @app_commands.command()
    async def join(self, interaction: discord.Interaction):  # funktioniert
        """
        Der Bot wird in den Channel mit dem Autor Connectet
        """
        await interaction.response.defer()
        ctx = await commands.Context.from_interaction(interaction)
        await self.musicClient.join(ctx=ctx)

    @app_commands.command()
    async def leave(self, interaction: discord.Interaction):  # funktioniert
        """
        Wenn der Bot in einem Channel ist, wird dieser disconnectet
        """
        await interaction.response.defer()
        ctx = await commands.Context.from_interaction(interaction)
        await self.musicClient.leave(ctx=ctx)

    @app_commands.command()
    async def play_queue(self, interaction: discord.Interaction):  # funktioniert
        """
        Spielt alle Songs ab, die bisher gesucht worden sind
        """
        await interaction.response.defer()
        ctx = await commands.Context.from_interaction(interaction)
        await self.musicClient.play_queue(ctx=ctx)

    @app_commands.command()
    @app_commands.describe(song="Dein Song")
    async def play(self, interaction: discord.Interaction, song: str):  # funktioniert
        """
        Fügt das gesuchte Lied der Queue zu, spielt bei Gelegenheit ab
        """
        await interaction.response.defer()
        ctx = await commands.Context.from_interaction(interaction)
        await self.musicClient.play(ctx=ctx, song=song)

    @app_commands.command()
    async def stop(self, interaction: discord.Interaction):  # funktioniert
        """
        Stopt das Lied, wenn eins gespielt wird
        """
        await interaction.response.defer()
        ctx = await commands.Context.from_interaction(interaction)
        await self.musicClient.stop(ctx=ctx)

    @app_commands.command()
    async def pause(self, interaction: discord.Interaction):  # funktioniert
        """
        Pausiert das momentan gespielte Lied
        """
        await interaction.response.defer()
        ctx = await commands.Context.from_interaction(interaction)
        await self.musicClient.pause(ctx=ctx)

    @app_commands.command()
    async def resume(self, interaction: discord.Interaction):  # funktioniert
        """
        Gibt das momentan pausierte Lied wieder
        """
        await interaction.response.defer()
        ctx = await commands.Context.from_interaction(interaction)
        await self.musicClient.resume(ctx=ctx)

    @app_commands.command()
    async def repeat(self, interaction: discord.Interaction):  # funktioniert
        """
        Spielt das letzt gespielte Lied als nächstes ab
        """
        await interaction.response.defer()
        ctx = await commands.Context.from_interaction(interaction)
        await self.musicClient.repeat(ctx=ctx)


class Client_Prefix_Commands(commands.Cog):
    def __init__(self, prefix: str, debug: bool):
        self.musicClient: MusicClient = MusicClient(prefix=prefix, debug=debug)
        self.debug = debug

    def getParamFromMessage(self, message: str) -> str:
        if self.debug:
            ic(message)

        message = message.split(" ")
        message.pop(0)

        newMessage = ""
        for element in message:
            newMessage = newMessage + element
            newMessage = newMessage + " "
        return newMessage

    #                                                        ---Admin-Commands---
    @commands.command()
    @has_permissions()
    async def preboot(self, ctx: commands.Context):
        """Rebootet den Bot"""
        await self.musicClient.reboot(ctx=ctx)

    @commands.command()
    @has_permissions()
    async def penable_debug(self, ctx: commands.Context):
        """ONLY FOR BOT OWNER: Logs Information on console"""
        await self.musicClient.enable_debug(ctx=ctx)

    @commands.command()
    @has_permissions()
    async def pget_all_ideas(self, ctx: commands.Context):
        """
        ONLY FOR BOT OWNER:
        Logs Ideas from other people on console
        """
        await self.musicClient.get_all_ideas(ctx=ctx)

    #                                                        ---Commands---

    @commands.command()
    async def pinvite(self, ctx: commands.Context):
        inv = await ctx.channel.create_invite()
        await ctx.send("Click below to invite someone", view=InviteButtons(str(inv)))

    @commands.command()
    async def pping_hello(self, ctx: commands.Context):
        await self.musicClient.ping_hello(ctx=ctx)

    @commands.command()
    async def pskip(self, ctx: commands.Context):  # TODO
        """
        Stoppt das Aktuelle Lied und spielt dann das nächste
        """
        steps: str = self.getParamFromMessage(message=ctx.content.message)
        await self.musicClient(ctx, steps)

    @app_commands.command()
    async def pshuffle(self, ctx: commands.Context):
        """Enables randommode"""
        await self.musicClient.shuffle(ctx=ctx)

    @commands.command()  # TODO get idee
    async def pidee(self, ctx: commands.Context, idee: str):
        """
        Gebe dein Wunsch an, der dir an diesem Bot fehlt. Dies wird versucht in diesem Bot zuverwirklichen!
        """
        idee: str = self.getParamFromMessage(message=ctx.content.message)
        await self.musicClient.idee(ctx=ctx, idee=idee)

    @commands.command()
    async def pclear_queue(self, ctx: commands.Context):  # funktioniert
        """Leert die Queue"""
        await self.musicClient.clear_queue(ctx=ctx)

    @commands.command()
    async def psend_title(self, ctx: commands.Context):  # funktioniert
        """Gibt die Title der Queue aus"""
        await self.musicClient.send_title(ctx=ctx)

    @commands.command()
    async def psend_link(self, ctx: commands.Context):  # funktioniert
        """Gibt die Title der Queue aus"""
        await self.musicClient.send_link(ctx=ctx)

    @commands.command()
    async def ploop(self, ctx: commands.Context):  # funktioniert
        """Aktiviert eine Endloss Schleife"""
        await self.musicClient.loop(ctx=ctx)

    @commands.command()
    async def pjoin(self, ctx: commands.Context):  # funktioniert
        """Der Bot wird in den Channel mit dem Autor Connectet"""
        await self.musicClient.join(ctx=ctx)

    @commands.command()
    async def pleave(self, ctx: commands.Context):  # funktioniert
        """Wenn der Bot in einem Channel ist, wird dieser disconnectet"""
        await self.musicClient.leave(ctx=ctx)

    @commands.command()
    async def pplay_queue(self, ctx: commands.Context):  # funktioniert
        """Spielt alle Songs ab, die bisher gesucht worden sind"""
        await self.musicClient.play_queue(ctx=ctx)

    @commands.command()
    async def pplay(self, ctx: commands.Context, song: str):  # funktioniert
        """Fügt das gesuchte Lied der Queue zu, spielt bei Gelegenheit ab"""
        song: str = self.getParamFromMessage(message=ctx.content.message)
        await self.musicClient.play(ctx=ctx, song=song)

    @commands.command()
    async def pstop(self, ctx: commands.Context):  # funktioniert
        """Stopt das Lied, wenn eins gespielt wird"""
        await self.musicClient.stop(ctx=ctx)

    @commands.command()
    async def ppause(self, ctx: commands.Context):  # funktioniert
        """Pausiert das momentan gespielte Lied"""
        await self.musicClient.pause(ctx=ctx)

    @commands.command()
    async def presume(self, ctx: commands.Context):  # funktioniert
        """Gibt das momentan pausierte Lied wieder"""
        await self.musicClient.resume(ctx=ctx)

    @commands.command()
    async def prepeat(self, ctx: commands.Context):  # funktioniert
        """Spielt das letzt gespielte Lied als nächstes ab"""
        await self.musicClient.repeat(ctx=ctx)


class Fun(commands.Cog):
    def __init__(self, debug: bool) -> None:
        self.debug: bool = debug
        ic("Spielburg geladen")

    def getSongJson(self):
        with open(
            f"{os.path.join(os.path.dirname(os.path.realpath(__file__)))}\\song.json",
            "r",
        ) as file:
            data = file.read()
            data = json.loads(data)
            file.close()
        return data

    def setZitate(self, arg: dict):
        data: dict[list[dict[str, str]]] = self.getSongJson()
        with open(
            f"{os.path.join(os.path.dirname(os.path.realpath(__file__)))}\\song.json",
            "w",
        ) as file:
            liste: list = data["Zitate"]
            liste.append(arg)
            data["Zitate"] = liste
            json.dump(data, file, sort_keys=True, indent=4)
            file.close()

    async def schreibe(self, ctx, userid: int, message: str):
        """Schreibt die Nachricht zwischen Befehl und Id an die Id"""
        user = client.get_user(int(userid))
        await user.send(message)

    async def zitat(self, ctx):
        """Sendet ein Zitat"""
        data = self.getSongJson()
        zitate: list = data["Zitate"]
        i = random.randint(0, len(zitate) - 1)
        await ctx.send(zitate[i])

    async def append_zitat(self, ctx, zitat: str):
        """Fügt der Zitatenliste das neue Zitat hinzu"""
        self.setZitate(zitat)
        if self.debug:
            ic(zitat)
        await ctx.send(f"Folgendes Zitat wurde der Liste hinzugefügt: {zitat}")

    async def zitatiere(self, ctx, userid: str):
        """Sendet der Id ein zufälliges Zitat zu"""
        data = self.getSongJson()
        zitate: list = data["Zitate"]
        i = random.randint(0, len(zitate) - 1)
        user = client.get_user(int(userid))
        await ctx.send(f"{zitate[i]} wurde gesendet an die Id: {userid}")
        await user.send(zitate[i])


class Fun_Slash_Commands(commands.Cog):
    def __init__(self, debug) -> None:
        self.spieleBurg = Fun(debug=debug)

    @app_commands.command()
    @app_commands.describe(userid="UserId", message="Deine Nachricht")
    async def schreibe(
        self, interaction: discord.Interaction, userid: int, message: str
    ):
        """Schreibt die Nachricht zwischen Befehl und Id an die Id"""
        await interaction.response.defer()
        ctx = await commands.Context.from_interaction(interaction)
        self.spieleBurg.schreibe(ctx=ctx, userid=userid, message=message)

    @app_commands.command()
    async def zitat(self, interaction: discord.Interaction):
        """Sendet ein Zitat"""
        await interaction.response.defer()
        ctx = await commands.Context.from_interaction(interaction)
        await self.spieleBurg.zitat(ctx=ctx)

    @app_commands.command()
    @app_commands.describe(zitat="Dein Zitat")
    async def append_zitat(self, interaction: discord.Interaction, zitat: str):
        """Fügt der Zitatenliste das neue Zitat hinzu"""
        await interaction.response.defer()
        ctx = await commands.Context.from_interaction(interaction)
        await self.spieleBurg.append_zitat(ctx=ctx, zitat=zitat)

    @app_commands.command()
    @app_commands.describe(userid="UserId")
    async def zitatiere(self, interaction: discord.Interaction, userid: str):
        """Sendet der Id ein zufälliges Zitat zu"""
        await interaction.response.defer()
        ctx = await commands.Context.from_interaction(interaction)
        await self.spieleBurg.zitatiere(ctx=ctx, userid=userid)


class Fun_Prefix_Commands(commands.Cog):
    def __init__(self, debug) -> None:
        self.spieleBurg = Fun(debug=debug)

    def getParamFromMessage(self, message: str) -> str:
        if self.debug:
            ic(message)

        message = message.split(" ")
        message.pop(0)

        newMessage = ""
        for element in message:
            newMessage = newMessage + element
            newMessage = newMessage + " "
        return newMessage

    @commands.command()
    async def schreibe(self, ctx: commands.Context):
        """Schreibt die Nachricht zwischen Befehl und Id an die Id"""
        msg: list = self.getParamFromMessage(message=ctx.content.message).spilt(" ")

        userid = int(msg.pop(0))
        newMessage = ""
        for element in msg:
            newMessage = newMessage + element
            newMessage = newMessage + " "

        self.spieleBurg.schreibe(ctx=ctx, userid=userid, message=newMessage)

    @commands.command()
    async def zitat(self, ctx: commands.Context):
        """Sendet ein Zitat"""
        await self.spieleBurg.zitat(ctx=ctx)

    @commands.command()
    async def append_zitat(self, ctx: commands.Context):
        """Fügt der Zitatenliste das neue Zitat hinzu"""
        zitat: str = self.getParamFromMessage(ctx.content.message)
        await self.spieleBurg.append_zitat(ctx=ctx, zitat=zitat)

    @commands.command()
    async def zitatiere(self, ctx: commands.Context):
        """Sendet der Id ein zufälliges Zitat zu"""
        userid = int(self.getParamFromMessage(ctx.content.message))
        await self.spieleBurg.zitatiere(ctx=ctx, userid=userid)


# Projekt auf ICE
class Webuntis(commands.Cog):
    def __init__(self, debug: bool, settings: dict | None) -> None:
        """
        Soll alles was in der Schule gebraucht wird abfragen können.
        """
        self.debug: bool = debug
        if settings is None:
            raise ValueError("Settings are not given")

        self.s = webuntis.Session(
            server=settings.get("link"),
            username=settings.get("username"),
            password=settings.get("password"),
            school=settings.get("school"),
            useragent=settings.get("user_agent"),
        )
        ic("Webuntis geladen")

    async def freier_raum(self, interaction: discord.Interaction):
        """
        soll Freieräume anzeigen, außer spezielle Fachräume: wo Computer stehen
        """
        await interaction.response.defer()
        ctx = await commands.Context.from_interaction(interaction)
        data = self.s.rooms()
        await ctx.send(
            "soll Freieräume anzeigen, außer spezielle Fachräume: wo Computer stehen"
        )


class Webuntis_Slash_Commands(commands.Cog):
    def __init__(self, debug, settings) -> None:
        self.untis: Webuntis = Webuntis(debug=debug, settings=settings)
        self.debug: bool = debug

    @app_commands.command()
    async def freier_raum(self, interaction: discord.Interaction):
        """
        soll Freieräume anzeigen, außer spezielle Fachräume: wo Computer stehen
        """
        await interaction.response.defer()
        ctx = await commands.Context.from_interaction(interaction)
        await self.untis.freier_raum(ctx=ctx)


class Webuntis_Prefix_Commands(commands.Cog):
    def __init__(self, debug, settings) -> None:
        self.untis: Webuntis = Webuntis(debug=debug, settings=settings)
        self.debug: bool = debug

    def getParamFromMessage(self, message: str) -> str:
        if self.debug:
            ic(message)

        message = message.split(" ")
        message.pop(0)

        newMessage = ""
        for element in message:
            newMessage = newMessage + element
            newMessage = newMessage + " "
        return newMessage

    @app_commands.command()
    async def pfreier_raum(self, interaction: discord.Interaction):
        """
        soll Freieräume anzeigen, außer spezielle Fachräume: wo Computer stehen
        """
        await interaction.response.defer()
        ctx = await commands.Context.from_interaction(interaction)
        await self.untis.freier_raum(ctx=ctx)


if __name__ == "__main__":
    TOKEN = bot_settings.get("token")
    client.run(token=TOKEN)

    """
    settings.json sollte so aussehen:

    {
        "settings_bot": {
            "prefix":"",
            "ownerId":,
            "token": ""
        },
        "settings_Webuntis": {
            "link":"",
            "username": "",
            "password": "",
            "school":"",
            "user_agent":""
        }
    }
    """
