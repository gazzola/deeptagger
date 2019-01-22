import logging
from functools import partial

import torch
from torchtext.vocab import Vectors

from deeptagger.constants import UNK, PAD, START, STOP


class WordEmbeddings(Vectors):

    def __init__(self, name, emb_format='polyglot', binary=True,
                 map_fn=lambda x: x, save_vectors=False, **kwargs):
        """
        Arguments:
           emb_format: the saved embedding model format, choices are:
                       polyglot, word2vec, fasttext and glove
           binary: only for word2vec and fasttext
           map_fn: a function that maps special original tokens
                       to Polyglot tokens (e.g. <eos> to </S>)
           save_vectors: save a vectors cache
        """
        self.itos = []
        self.stoi = {}
        self.dim = None
        self.vectors = None
        self.binary = binary
        self.emb_format = emb_format
        self.map_fn = map_fn
        self.save_vectors = save_vectors
        super().__init__(name, **kwargs)

    def __getitem__(self, token):
        if token in self.stoi:
            token = self.map_fn(token)
            return self.vectors[self.stoi[token]]
        else:
            return self.unk_init(torch.Tensor(1, self.dim))

    def cache(self, name, cache, url=None, max_vectors=None):
        if self.emb_format in ['polyglot', 'glove']:
            from polyglot.mapping import Embedding
            if self.emb_format == 'polyglot':
                embeddings = Embedding.load(name)
            else:
                embeddings = Embedding.from_glove(name)
            self.itos = embeddings.vocabulary.id_word
            self.stoi = embeddings.vocabulary.word_id
            self.dim = embeddings.shape[1]
            self.vectors = torch.Tensor(embeddings.vectors).view(-1, self.dim)
        elif self.emb_format in ['word2vec', 'fasttext']:
            try:
                from gensim.models import KeyedVectors
            except ImportError:
                logging.error('Please install `gensim` package first.')

            embeddings = KeyedVectors.load_word2vec_format(
                name, unicode_errors='ignore', binary=self.binary
            )
            self.itos = embeddings.index2word
            self.stoi = dict(zip(self.itos, range(len(self.itos))))
            self.dim = embeddings.vector_size
            self.vectors = torch.Tensor(embeddings.vectors).view(-1, self.dim)


def to_polyglot(token):
    mapping = {
        UNK: '<UNK>',
        PAD: '<PAD>',
        START: '<S>',
        STOP: '</S>'
    }
    if token in mapping:
        return mapping[token]
    return token


Polyglot = partial(WordEmbeddings, emb_format='polyglot', map_fn=to_polyglot)
Word2Vec = partial(WordEmbeddings, emb_format='word2vec')
FastText = partial(WordEmbeddings, emb_format='fasttext')
Glove = partial(WordEmbeddings, emb_format='glove')

AvailableEmbeddings = {
    'polyglot': Polyglot,
    'word2vec': Word2Vec,
    'fasttext': FastText,
    'glove': Glove
}
