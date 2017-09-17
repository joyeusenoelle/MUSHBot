import re, random
import libs.markov as markov
import libs.wiki as wiki
import libs.log as logger
import libs.ingen as ingen
import libs.weather as weather
import importlib as imp
from time import sleep

# To do:
# * Log all lines that get caught by the text matcher and all lines sent by the bot
# * Improve the Markov class's predictive text algorithm
# * Write Javascript that hides and shows OOC text, add it to the beginning of logs


def reloadall():
    """ Reloads all of the custom modules. Needs to be integrated into the
        new Lib object.
    """
    imp.reload(markov)
    imp.reload(wiki)
    imp.reload(logger)
    getreminders()

class Lib:
    def __init__(self, name, owner, prnt, config):
        """ Initialize MUSHBot libraries. Required parameters:
            name (str) - the MUSH name of the MUSHBot object
            owner (str) - the MUSH name of the MUSHBot object's owner
            prnt (object) - the object handling output.
            config (dict) - the current configuration
        """
        self.name = str(name)
        self.owner = str(owner)
        self.prnt = prnt
        self.options = config
        self.ooc = None
        self.logging = False
        self.reminders = {}
        self.makeRegexes()
        self.otherr = re.compile(r"([^\[]+) \[to {}\]: (.+)".format(self.name))
        self.getreminders()
        self.markov = markov.Markov(self.prnt)
        self.wiki = wiki.Wiki(self.prnt)
        self.logger = logger.Log(self.prnt, self.options)
        self.ingen = ingen.INGen(self.prnt)
        self.weather = weather.Weather(self.prnt)
        self.responses = ["It is certain.",
            "It is decidedly so.",
            "Without a doubt.",
            "Yes, definitely.",
            "You may rely on it.",
            "As I see it, yes.",
            "Most likely.",
            "Outlook good.",
            "Yes.",
            "Signs point to yes.",
            "Reply hazy. Try again.",
            "Ask again later.",
            "Better not tell you now.",
            "Cannot predict now.",
            "Concentrate and ask again.",
            "Don't count on it.",
            "My reply is no.",
            "My sources say no.",
            "Outlook not so good.",
            "Very doubtful."]

    def getreminders(self):
        """ Get reminders from a text file.
        """
        try:
            rfile = open('reminders.txt', 'r+')
            rtext = rfile.read()
            self.reminders = eval(rtext)
            rfile.close()
        except:
            rfile = open('reminders.txt', 'w')
            rfile.close()

    def textmatch(self, text):
        """ The workhorse function. Takes text and matches it against a
        bunch of regexes to see what to do. This and everything it imports
        can be reloaded without reloading the bot itself.
        """
        if self.logging:
            self.logger.appendLog(text)

        for regex, func in self.regexes.items():
            match = regex.search(text)
            if match:
                return func(match)

        # Preserving order without sorting.
        # If someone has said something to MUSHBot that it can't recognize
        match = self.otherr.search(text)
        if match:
            return self.other(match)

    def setic(self, match):
        """ Is an in-character scene running? Then add a prefix to mark MUSHBot
            as OOC (out of character). This triggers if MUSHBot sees a scene
            start or if an on-MUSH object tells MUSHBot a scene is in progress
            when MUSHBot connects.
        """
        self.ooc = ">"
        self.lstart(None)
        return None

    def setooc(self, match):
        """ Is the in-character scene over? Then remove the prefix from
            MUSHBot's text.
        """
        self.ooc = None
        self.lstop()
        return None

    def amiooc(self, match):
        """ Finds out whether MUSHBot is set to use an prefix to mark its text as
            OOC (out-of-character), and indicates the prefix MUSHBot is using
            if so.
        """
        if self.ooc == None:
            return "{}We're not in a scene, so I'm not using a prefix.".format(self.ooc or "\"")
        else:
            return "{}We might be in a scene, so I'm using this prefix: {}".format(self.ooc or ">",self.ooc)

    def redesc(self, match):
        """ MUSHBot's owner can update the on-MUSH string describing what MUSHBot can do.
        """
        return "@set me=STR-WHATCANIDO:{}\np {}=Updated STR-WHATCANIDO.\n".format(match.group(1), self.owner)

    def markov(self, match):
        """ Returns a paragraph of text generated by running a Markov chain
            over one of several corpora.
        """
        return self.markov.getChain(match.group(2), match.group(1), self.ooc)

    def wiki(self, match):
        """ Returns the first few paragraphs of a Wikipedia entry for the
            requested topic.
        """
        return self.wiki.getWiki(match.group(2), match.group(1), self.ooc)

    def weather(self, match):
        """ Returns the weather report for the requested location.
        """
        return self.weather.getWeather(match.group(2), self.ooc)

    def lstart(self, match):
        """ Start logging if there isn't a log running.
            Accepts an optional list of players, which will highlight their
            text in different colors in the log.
        """
        if self.logging == True:
            return "{}I'm already logging, and currently can't do more than one at once.".format(self.ooc or "\"")
        else:
            self.logging = True
            self.players = None
            if match != None and match.group(2):
                self.players = match.group(2)
            self.logger.startLog(self.players)
            return "{}Okay, I'm logging.".format(self.ooc or "\"")

    def lstop(self, match):
        """ Stop logging if there's a log running.
        """
        if self.logging == False:
            return "{}I'm not logging right now.".format(self.ooc or "\"")
        else:
            output = self.logger.stopLog()
            self.curlog = None
            self.logging = False
            return "{}I've stopped logging. {}".format(self.ooc or "\"", output)

    def globalr(self, match):
        """ If someone has sent MUSHBot a global greet, respond in kind.
        """
        if match.group(2)[-1] != "s":
            emote = match.group(2)
        else:
            emote = match.group(2)[:-1]
        return "{} {}".format(emote, match.group(1))

    def help(self, match):
        """ Quotes the on-MUSH string detailing MUSHBot's capabilities.
        """
        return "quote [u(me/STR-WHATCANIDO)]"

    def gnw(self, match):
        """ A WarGames joke.
        """
        return "{}'{} A strange game. The only winning move is not to play. How about a nice game of chess?".format(self.ooc or "", match.group(1))

    def remind(self, match):
        """ Create a reminder. So far the only available timeframe is "the
            next time the recipient logs in.
        """
        if match.group(2) != "next":
            return "{}I'm sorry, I don't recognize that timeframe.".format(self.ooc or "\"")
        if match.group(3) in self.reminders.keys():
            self.reminders[match.group(3)].append([match.group(1), match.group(4)])
        else:
            self.reminders[match.group(3)] = [[match.group(1), match.group(4)]]
        try:
            rfile = open('reminders.txt', 'w')
            rfile.write(str(self.reminders))
            rfile.close()
        except:
            return "{}I've saved the reminder temporarily, but I couldn't write to the backup file.".format(self.ooc or "\"")
        return "{}Okay, I'll remind them: {} asked me to say '{}'.".format(self.ooc or "\"", match.group(1), match.group(4))

    def login(self, match):
        """ If someone logs in and there's a reminder set for them, wait three
            seconds and then remind them.
        """
        if match.group(1) in self.reminders.keys():
            sleep(3)
            output = "{}'{} I have some messages for you!".format(self.ooc or "", match.group(1))
            for rem in self.reminders[match.group(1)]:
                output += " {} asked me to say '{}'.".format(rem[0], rem[1])
            del self.reminders[match.group(1)]
            with open('reminders.txt', 'w') as rfile:
                rfile.write(str(self.reminders))
            return output

    def inchar(self, match):
        """ If someone asks for a random In Nomine character.
        """
        args = None
        if match.group(2):
            args = match.group(2)
        #character = self.ingen.createCharacter(args, ret=True)
        character = self.ingen.createCharacter(ret=True)
        character = character.replace("\n","%r")
        character = character.replace("\t","%t")
        return "quote {}".format(character)

    def cmd(self, match):
        """ MUSHBot's owner can ask MUSHBot to execute arbitrary MUSH commands.
            (This is limited to commands the bot can execute.)
        """
        return "{}".format(match.group(1))

    def draw(self):
        """ Ridiculousness.
        """
        return "{}:hands {} a picture of a cow.".format(self.ooc or "", match.group(1))

#    def kellyanne(self,match):
#        with open("countries.txt", "r") as f:
#            countries = f.read().split("\n")
#        with open("attack_types.txt","r") as f:
#            attack_types = f.read().split("\n")
#        with open("us_places.txt","r") as f:
#            us_places = f.read().split("\n")
#        text_strings = ["Remember the {0} {1} - why we must restrict immigrants from {2}.","We have to protect ourselves from {2} because of the {0} {1}.","The media didn't report the {1} in {0}. No more aggression from {2}!","How can we admit refugees from {2} after the {1} in {0}?","We must close our borders against {2} because of the {0} {1}."]
#        tweet = random.choice(text_strings).format(random.choice(us_places),random.choice(attack_types),random.choice(countries))
#        return "{}'{} {}".format(self.ooc or "",match.group(1),tweet)

    def other(self,match):
        """ If the text is directed to MUSHBot, but it doesn't match any of the
            regular expressions, MUSHBot will respond with:
            * an 8-Ball answer if the text is a question
            * "I didn't understand" otherwise
        """
        if match.group(2)[-1] == "?":
            return "{}'{} {}".format(self.ooc or "", match.group(1), random.choice(self.responses))
        return "{}'{} Sorry, I didn't understand this: {}".format(self.ooc or "",match.group(1),match.group(2))



    def makeRegexes(self):
        """ Creates the regular expressions. These are defined after the rest
            of the functions so they don't throw errors. (This may be
            unnecessary.)
        """
        self.regexes = { re.compile(r"([^\[]+) \[to {0}\]: [Mm][Aa][Rr][Kk][Oo][Vv] (.+)".format(self.name)): self.markov,
            re.compile(r"([^\[]+) \[to {0}\]: [Ww][Ii][Kk][Ii] (.+)".format(self.name)): self.wiki,
            re.compile(r"{0} pages: desc (.+)".format(self.owner)): self.redesc,
            re.compile(r"Dicebag pages: .+"): self.setic,
            re.compile(r"<<Scene Start>>"): self.setic,
            re.compile(r"<<Scene Stop>>"): self.setooc,
            re.compile(r"\[to {0}\]: ooc?".format(self.name)): self.amiooc,
            re.compile(r"([^\[]+) \[to {0}\]: log start[ ]?(.*)".format(self.name)): self.lstart,
            re.compile(r"\[to {0}\]: log stop".format(self.name)): self.lstop,
            re.compile(r"\[Private\] ([^ ]+) ([^ ]+) [to ]*{0}!".format(self.name)): self.globalr,
            re.compile(r"\[to {0}\]: help".format(self.name)): self.help,
            re.compile(r"([^\[]+) \[to {0}\]: .*[Tt]hermonuclear [Wwar].*".format(self.name)): self.gnw,
            re.compile(r"([^\[]+) \[to {0}\]: remind ([^ ]+) ([^ ]+) (.+)".format(self.name)): self.remind,
            re.compile(r"([^\[]+) has connected."): self.login,
            re.compile(r"([^\[]+) \[to {0}\]: inchar[ ]?(.*)".format(self.name)): self.inchar,
            re.compile(r"{0} pages: command (.+)".format(self.owner)): self.cmd,
            re.compile(r"([^\[]+) \[to {0}\]: draw".format(self.name)): self.draw,
            re.compile(r"([^\[]+) \[to {0}\]: weather (.+)".format(self.name)): self.weather
#            re.compile(r"([^\[]+) \[to {0}\]: kellyanne".format(self.name)): self.kellyanne
        }
