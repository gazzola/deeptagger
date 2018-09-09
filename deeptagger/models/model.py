import logging
from abc import ABCMeta, abstractmethod

import torch


class Model(torch.nn.Module):
    __metaclass__ = ABCMeta

    def __init__(self,
                 words_field,
                 tags_field,
                 prefixes_field=None,
                 suffixes_field=None,
                 caps_field=None):
        super().__init__()
        # Default fields and embeddings
        self.words_field = words_field
        self.tags_field = tags_field
        # Extra features
        self.prefixes_field = prefixes_field
        self.suffixes_field = suffixes_field
        self.caps_field = caps_field
        # Building flag
        self.is_built = False
        # Loss function has to be defined in build()
        self._loss = None

    @property
    def nb_classes(self):
        return len(self.tags_field.vocab.stoi)

    def loss(self, pred, gold):
        # (bs*ts, nb_classes)
        predicted = pred.reshape(-1, self.nb_classes)

        # (bs*ts, )
        gold = gold.reshape(-1)

        return self._loss(predicted, gold)

    @abstractmethod
    def build(self, **params):
        pass

    @abstractmethod
    def forward(self, *args, **kwargs):
        pass

    def predict_proba(self, batch):
        pred = self.forward(batch)
        return torch.exp(pred)  # assume log softmax in the output

    def predict_classes(self, batch):
        _, classes = torch.max(self.predict_proba(batch), -1)
        return classes

    def load(self, path):
        logging.debug("Loading model weights from {}".format(path))
        self.load_state_dict(
            torch.load(str(path), map_location=lambda storage, loc: storage)
        )

    def save(self, path):
        logging.debug("Saving model weights to {}".format(path))
        torch.save(self.state_dict(), str(path))
