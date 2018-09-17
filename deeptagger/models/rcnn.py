import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.nn.utils.rnn import pack_padded_sequence as pack
from torch.nn.utils.rnn import pad_packed_sequence as unpack

from deeptagger import constants
from deeptagger.models.model import Model


class RCNN(Model):
    """Recurrent Convolutional Neural Network.
    As described in: https://arxiv.org/pdf/1610.00211.pdf
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # layers
        self.word_emb = None
        self.prefixes_emb = None
        self.prefix_length = None
        self.suffixes_emb = None
        self.suffix_length = None
        self.caps_emb = None
        self.caps_length = None
        self.dropout_emb = None
        self.cnn_1d = None
        self.max_pool = None
        self.is_bidir = None
        self.sum_bidir = None
        self.gru = None
        self.hidden = None
        self.dropout_gru = None
        self.linear_out = None
        self.relu = None
        self.sigmoid = None

    def build(self, options):
        # prefix_embeddings_size = options.prefix_embeddings_size
        # suffix_embeddings_size = options.suffix_embeddings_size
        # caps_embeddings_size = options.caps_embeddings_size
        hidden_size = options.hidden_size[0]
        loss_weights = None
        if options.loss_weights == 'balanced':
            # TODO
            # loss_weights = calc_balanced(loss_weights, tags_field)
            loss_weights = torch.FloatTensor(loss_weights)

        word_embeddings = None
        if self.words_field.vocab.vectors is not None:
            word_embeddings = self.words_field.vocab.vectors
            options.word_embeddings_size = word_embeddings.size(1)

        self.word_emb = nn.Embedding(
            num_embeddings=len(self.words_field.vocab),
            embedding_dim=options.word_embeddings_size,
            padding_idx=constants.PAD_ID,
            _weight=word_embeddings,
        )

        features_size = options.word_embeddings_size
        if self.prefixes_field is not None:
            self.prefixes_emb = nn.Embedding(
                num_embeddings=len(self.prefixes_field.vocab),
                embedding_dim=options.prefix_embeddings_size,
                padding_idx=constants.PAD_ID
            )
            self.prefix_length = (options.prefix_max_length -
                                  options.prefix_min_length + 1)
            features_size += (self.prefix_length *
                              options.prefix_embeddings_size)

        if self.suffixes_field is not None:
            self.suffixes_emb = nn.Embedding(
                num_embeddings=len(self.suffixes_field.vocab),
                embedding_dim=options.suffix_embeddings_size,
                padding_idx=constants.PAD_ID
            )
            self.suffix_length = (options.suffix_max_length -
                                  options.suffix_min_length + 1)
            features_size += (self.suffix_length *
                              options.suffix_embeddings_size)

        if self.caps_field is not None:
            self.caps_emb = nn.Embedding(
                num_embeddings=len(self.caps_field.vocab),
                embedding_dim=options.caps_embeddings_size,
                padding_idx=constants.PAD_ID
            )
            self.caps_length = 1
            features_size += options.caps_embeddings_size

        if options.freeze_embeddings:
            self.word_emb.weight.requires_grad = False
            self.word_emb.bias.requires_grad = False
            if self.prefixes_field is not None:
                self.prefixes_emb.weight.requires_grad = False
                self.prefixes_emb.bias.requires_grad = False
            if self.suffixes_field is not None:
                self.suffixes_emb.weight.requires_grad = False
                self.suffixes_emb.bias.requires_grad = False
            if self.caps_field is not None:
                self.caps_emb.weight.requires_grad = False
                self.caps_emb.bias.requires_grad = False

        self.dropout_emb = nn.Dropout(options.emb_dropout)

        self.cnn_1d = nn.Conv1d(in_channels=features_size,
                                out_channels=options.conv_size,
                                kernel_size=options.kernel_size,
                                padding=options.kernel_size // 2)

        self.max_pool = nn.MaxPool1d(options.pool_length,
                                     padding=options.pool_length // 2)

        self.is_bidir = options.bidirectional
        self.sum_bidir = options.sum_bidir
        self.gru = nn.GRU(options.conv_size // options.pool_length +
                          options.pool_length // 2,
                          hidden_size,
                          bidirectional=self.is_bidir,
                          batch_first=True)
        self.hidden = None
        self.dropout_gru = nn.Dropout(options.dropout)

        n = 2 if self.is_bidir else 1
        n = 1 if self.sum_bidir else n
        self.linear_out = nn.Linear(n * hidden_size, self.nb_classes)

        self.relu = torch.nn.ReLU()
        self.sigmoid = torch.nn.Sigmoid()

        self.init_weights()

        # Loss
        self._loss = nn.NLLLoss(weight=loss_weights,
                                ignore_index=constants.TAGS_PAD_ID)
        self.is_built = True

    def init_weights(self):
        torch.nn.init.xavier_uniform_(self.cnn_1d.weight)
        torch.nn.init.constant_(self.cnn_1d.bias, 0.)
        torch.nn.init.xavier_uniform_(self.gru.weight_ih_l0)
        torch.nn.init.xavier_uniform_(self.gru.weight_hh_l0)
        torch.nn.init.constant_(self.gru.bias_ih_l0, 0.)
        torch.nn.init.constant_(self.gru.bias_hh_l0, 0.)
        torch.nn.init.xavier_uniform_(self.linear_out.weight)
        torch.nn.init.constant_(self.linear_out.bias, 0.)
        if self.is_bidir:
            torch.nn.init.xavier_uniform_(self.gru.weight_ih_l0_reverse)
            torch.nn.init.xavier_uniform_(self.gru.weight_hh_l0_reverse)
            torch.nn.init.constant_(self.gru.bias_ih_l0_reverse, 0.)
            torch.nn.init.constant_(self.gru.bias_hh_l0_reverse, 0.)

    def init_hidden(self, batch_size, hidden_size):
        # The axes semantics are (num_layers, minibatch_size, hidden_dim)
        num_layers = 2 if self.is_bidir else 1
        return torch.zeros(num_layers, batch_size, hidden_size)

    def forward(self, batch):
        assert self.is_built

        bs, ts = batch.words.shape
        h = batch.words
        mask = h != constants.PAD_ID
        lengths = mask.int().sum(dim=-1)

        # initialize GRU hidden state
        self.hidden = self.init_hidden(h.shape[0], self.gru.hidden_size)

        # (bs, ts) -> (bs, ts, emb_dim)
        h = self.word_emb(h)

        feats = [h]
        if self.prefixes_field is not None:
            # (bs, (ts-2)*(maxlen-minlen+1)) ->
            # (bs, (ts-2)*(max-min+1), emb_dim)
            h_pre = self.prefixes_emb(batch.prefixes)
            # (bs, (ts-2)*(max-min+1), emb_dim) ->
            # (bs, ts*(max-min+1), emb_dim)
            z = torch.zeros(h_pre.shape[0], self.prefix_length, h_pre.shape[2])
            h_pre = torch.cat((z, h_pre, z), dim=1)
            # (bs, ts*(max-min+1), emb_dim) -> (bs, ts, emb_dim*(max-min+1))
            h_pre = h_pre.view(bs, ts, -1)
            feats.append(h_pre)

        if self.suffixes_field is not None:
            h_suf = self.suffixes_emb(batch.suffixes)
            z = torch.zeros(h_suf.shape[0], self.suffix_length, h_suf.shape[2])
            h_suf = torch.cat((z, h_suf, z), dim=1)
            h_suf = h_suf.view(bs, ts, -1)
            feats.append(h_suf)

        if self.caps_field is not None:
            h_cap = self.caps_emb(batch.caps)
            z = torch.zeros(h_cap.shape[0], self.caps_length, h_cap.shape[2])
            h_cap = torch.cat((z, h_cap, z), dim=1)
            feats.append(h_cap)

        if feats:
            h = torch.cat(feats, dim=-1)

        h = self.dropout_emb(h)

        # Turn (bs, ts, emb_dim) into (bs, emb_dim, ts) for CNN
        h = h.transpose(1, 2)

        # (bs, emb_dim, ts) -> (bs, conv_size, ts)
        h = self.relu(self.cnn_1d(h))

        # Turn (bs, conv_size, ts) into (bs, ts, conv_size) for Pooling
        h = h.transpose(1, 2)

        # (bs, ts, conv_size) -> (bs, ts, pool_size)
        h = self.max_pool(h)

        # (bs, ts, pool_size) -> (bs, ts, hidden_size)
        h = pack(h, lengths, batch_first=True)
        h, self.hidden = self.gru(h, self.hidden)
        h, _ = unpack(h, batch_first=True)
        h = self.dropout_gru(h)

        # if you'd like to sum instead of concatenate:
        if self.sum_bidir:
            h = (h[:, :, :self.gru.hidden_size] +
                 h[:, :, self.gru.hidden_size:])

        # (bs, ts, hidden_size) -> (bs, ts, nb_classes)
        h = F.log_softmax(self.linear_out(h), dim=-1)

        # remove <bos> and <eos> tokens
        # (bs, ts, nb_classes) -> (bs, ts-2, nb_classes)
        h = h[:, 1:-1, :]

        return h
