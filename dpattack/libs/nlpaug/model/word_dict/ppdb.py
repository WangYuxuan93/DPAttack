try:
    import nltk
    from nltk.corpus import wordnet
except ImportError:
    # No installation required if not using this function
    pass

from dpattack.libs.nlpaug import PartOfSpeech
from dpattack.libs.nlpaug import WordDictionary


class Ppdb(WordDictionary):
    def __init__(self, dict_path):
        super().__init__(cache=True)

        self.dict_path = dict_path
        self.lang = 'eng'  # TODO: support other languages

        self.score_threshold = self.get_default_score_thresholds() # TODO: support other filtering
        self.is_synonym = True  # TODO: antonyms

        try:
            wordnet
        except NameError:
            raise ImportError('Missed nltk library. Install it via `pip install nltk`')

        self._init()

    def _init(self):
        self.dict = {}
        self.read(self.dict_path)

    @classmethod
    def get_default_score_thresholds(cls):
        return {
            'AGigaSim': 0.6
        }

    def read(self, model_path):
        with open(model_path, 'rb') as f:
            for line in f:
                line = line.decode('utf-8')

                if '\\ x' in line or 'xc3' in line:
                    continue

                fields = line.split('|||')
                constituents = fields[0].strip()[1:-1].split('/')
                phrase = fields[1].strip()
                paraphrase = fields[2].strip()
                features = fields[3].strip().split()
                features = [f for f in features for s in self.score_threshold if s in f]  # filter by scheme
                scores = []
                for feature in features:
                    scheme, score = feature.split('=')
                    if scheme in self.score_threshold and float(score) > self.score_threshold[scheme]:
                        scores.append((scheme, score))

                entailment = fields[5].strip()

                # filter multiple words
                if len(phrase.split()) != len(paraphrase.split()):
                    continue

                # filter equivalence word
                if entailment == 'Equivalence' and self.is_synonym:
                    continue

                # filter by feature/ score
                if len(scores) == 0:
                    continue

                if phrase not in self.dict:
                    self.dict[phrase] = {}

                part_of_speeches = [pos for con in constituents for pos in PartOfSpeech.constituent2pos(con)]

                for pos in part_of_speeches:
                    if pos not in self.dict[phrase]:
                        self.dict[phrase][pos] = []

                    self.dict[phrase][pos].append({
                        'phrase': phrase,
                        'part_of_speech': pos,
                        'synonym': paraphrase,
                        'scores': scores
                    })

    def predict(self, word, pos=None):
        if pos is None:
            candidates = []
            if word not in self.dict:
                return candidates

            for pos in self.dict[word]:
                for candidate in self.dict[word][pos]:
                    candidates.append(candidate['synonym'])

            return candidates

        if word in self.dict and pos in self.dict[word]:
            return [candidate['synonym'] for candidate in self.dict[word][pos]]

        return []

    def pos_tag(self, tokens):
        return nltk.pos_tag(tokens)
