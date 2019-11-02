"""
    Augmenter that apply operation to textual input based on word embeddings.
"""

from dpattack.libs.nlpaug import WordAugmenter
from dpattack.libs.nlpaug import Action
from dpattack.libs import nlpaug as nmw
from dpattack.libs.nlpaug.util.exception import WarningMessage


WORD2VEC_MODEL = None
GLOVE_MODEL = {}
FASTTEXT_MODEL = {}
model_types = ['word2vec', 'glove', 'fasttext']


def init_word2vec_model(model_path, force_reload=False, top_k=100):
    # Load models once at runtime
    global WORD2VEC_MODEL
    if WORD2VEC_MODEL and not force_reload:
        WORD2VEC_MODEL.top_k = top_k
        return WORD2VEC_MODEL

    word2vec = nmw.Word2vec(top_k=top_k)
    word2vec.read(model_path)
    WORD2VEC_MODEL = word2vec

    return WORD2VEC_MODEL


def init_glove_model(model_path, force_reload=False, top_k=None):
    # Load models once at runtime
    global GLOVE_MODEL
    if model_path in GLOVE_MODEL and not force_reload:
        GLOVE_MODEL[model_path].top_k = top_k
        return GLOVE_MODEL[model_path]

    glove = nmw.GloVe(top_k=top_k)
    glove.read(model_path)
    GLOVE_MODEL[model_path] = glove

    return GLOVE_MODEL[model_path]


def init_fasttext_model(model_path, force_reload=False, top_k=None):
    # Load models once at runtime
    global FASTTEXT_MODEL
    if model_path in FASTTEXT_MODEL and not force_reload:
        FASTTEXT_MODEL[model_path].top_k = top_k
        return FASTTEXT_MODEL[model_path]

    fasttext = nmw.Fasttext(top_k=top_k)
    fasttext.read(model_path)
    FASTTEXT_MODEL[model_path] = fasttext

    return FASTTEXT_MODEL[model_path]


class WordEmbsAug(WordAugmenter):
    """
    Augmenter that leverage word embeddings to find top n similar word for augmentation.

    :param str model_type: Model type of word embeddings. Expected values include 'word2vec', 'glove' and 'fasttext'.
    :param str model_path: Downloaded models directory. Either model_path or models is must be provided
    :param obj model: Pre-loaded models
    :param str action: Either 'insert or 'substitute'. If value is 'insert', a new word will be injected to random
        position according to word embeddings calculation. If value is 'substitute', word will be replaced according
        to word embeddings calculation
    :param int top_k: Controlling lucky draw pool. Top k score token will be used for augmentation. Larger k, more
        token can be used. Default value is 100. If value is None which means using all possible tokens.
    :param int aug_min: Minimum number of word will be augmented.
    :param float aug_p: Percentage of word will be augmented.
    :param int aug_n : Deprecated. Use top_k as alternative. Top n similar word for lucky draw
    :param list stopwords: List of words which will be skipped from augment operation.
    :param func tokenizer: Customize tokenization process
    :param func reverse_tokenizer: Customize reverse of tokenization process
    :param bool force_reload: If True, models will be loaded every time while it takes longer time for initialization.
    :param str name: Name of this augmenter

    >>> from dpattack.libs import nlpaug as naw
    >>> aug = naw.WordEmbsAug(model_type='word2vec', model_path='.')
    """

    def __init__(self, model_type, model_path='.', model=None, action=Action.SUBSTITUTE,
                 name='WordEmbs_Aug', aug_min=1, aug_p=0.3, top_k=20, aug_n=None, n_gram_separator='_',
                 stopwords=None, tokenizer=None, reverse_tokenizer=None, force_reload=False, verbose=0):
        super().__init__(
            action=action, name=name, aug_p=aug_p, aug_min=aug_min, stopwords=stopwords,
            tokenizer=tokenizer, reverse_tokenizer=reverse_tokenizer, verbose=verbose)

        self.model_type = model_type
        self.model_path = model_path

        self.top_k = top_k
        if aug_n is not None:
            print(WarningMessage.DEPRECATED.format('aug_n', '0.11.0', 'top_k'))
            self.top_k = aug_n
        self.n_gram_separator = n_gram_separator

        self.pre_validate()

        if model is None:
            self.model = self.get_model(model_type=model_type, force_reload=force_reload, top_k=self.top_k)
        else:
            self.model = model

    def pre_validate(self):
        if self.model_type not in model_types:
            raise ValueError('Model type value is unexpected. Expected values include {}'.format(model_types))

    def get_model(self, model_type, force_reload=False, top_k=100):
        if model_type == 'word2vec':
            return init_word2vec_model(self.model_path, force_reload, top_k=top_k)
        elif model_type == 'glove':
            return init_glove_model(self.model_path, force_reload, top_k=top_k)
        elif model_type == 'fasttext':
            return init_fasttext_model(self.model_path, force_reload, top_k=top_k)
        else:
            raise ValueError('Model type value is unexpected. Expected values include {}'.format(model_types))

    def skip_aug(self, token_idxes, tokens):
        results = []
        for token_idx in token_idxes:
            # Some words do not come with vector. It will be excluded in lucky draw.
            word = tokens[token_idx]

            if word in self.model.w2v:
                results.append(token_idx)

        return results

    def insert(self, data):
        tokens = self.tokenizer(data)
        results = tokens.copy()

        aug_idexes = self._get_random_aug_idxes(tokens)
        if aug_idexes is None:
            return data
        aug_idexes.sort(reverse=True)

        for aug_idx in aug_idexes:
            new_word = self.sample(self.model.get_vocab(), 1)[0]
            if self.n_gram_separator in new_word:
                new_word = new_word.split(self.n_gram_separator)[0]
            results.insert(aug_idx, new_word)

        return self.reverse_tokenizer(results)

    def substitute(self, data, aug_idxes=None):
        tokens = self.tokenizer(data)
        results = tokens.copy()
        if aug_idxes is None:
            aug_idxes = self._get_aug_idxes(tokens)
        if aug_idxes is None:
            return data

        candidate_list = []
        for aug_idx in aug_idxes:
            original_word = results[aug_idx]
            candidate_words = self.model.predict(original_word, n=1)
            #substitute_word = self.sample(candidate_words, 1)[0]
            candidate_list.append(candidate_words)

        return candidate_list, aug_idxes
