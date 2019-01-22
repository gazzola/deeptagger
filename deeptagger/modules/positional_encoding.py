import numpy as np
import torch
from torch import nn


class PositionalEncoding(nn.Module):
    """Implements the PE function."""

    def __init__(self, max_seq_len, size, dropout=0.0, scale=True):
        super().__init__()

        position = torch.arange(0.0, max_seq_len).unsqueeze(1)
        div_term = torch.exp(torch.arange(0.0, size, 2) * -(np.log(10000.0) / size))

        self.pe = torch.zeros(max_seq_len, size, requires_grad=False)
        if torch.cuda.is_available():
            self.pe = self.pe.cuda()
        self.pe[:, 0::2] = torch.sin(position * div_term)
        self.pe[:, 1::2] = torch.cos(position * div_term)
        self.pe = self.pe.unsqueeze(0)  # add batch dimension
        self.dropout = nn.Dropout(dropout)
        self.scale = scale
        self.size = size

    def forward(self, emb):
        assert (emb.shape[1] <= self.pe.shape[1])
        if self.scale:
            # multiplying weights according to the transformer
            emb = emb * np.sqrt(self.size)
        emb = emb + self.pe[:, :emb.shape[1]]
        emb = self.dropout(emb)
        return emb


if __name__ == '__main__':
    from matplotlib import pyplot as plt

    batch_size = 8
    vocab_size = 1000
    emb_size = 20
    seq_len = 100
    max_seq_len = 5000
    d_i, d_j = 4, 10

    x_emb = torch.randint(vocab_size, size=(batch_size, seq_len)).long()
    x_rand = torch.randn(batch_size, seq_len, emb_size)
    x_zero = torch.zeros(batch_size, seq_len, emb_size)

    embed = nn.Embedding(vocab_size, emb_size)
    torch.nn.init.xavier_normal_(embed.weight)
    pe = PositionalEncoding(max_seq_len, emb_size)

    x_rand = pe(x_rand)
    x_emb = pe(embed(x_emb)).data
    x_zero = pe(x_zero)

    plt.figure(figsize=(15, 5))
    plt.title('Random input')
    plt.plot(np.arange(seq_len), x_rand[0, :, d_i:d_j].numpy())
    plt.legend(['dim %d' % d for d in range(d_i, d_j)])
    plt.show()

    plt.figure(figsize=(15, 5))
    plt.title('Embedding input')
    plt.plot(np.arange(seq_len), x_emb[0, :, d_i:d_j].numpy())
    plt.legend(['dim %d' % d for d in range(d_i, d_j)])
    plt.show()

    plt.figure(figsize=(15, 5))
    plt.title('Zero input')
    plt.plot(np.arange(seq_len), x_zero[0, :, d_i:d_j].numpy())
    plt.legend(['dim %d' % d for d in range(d_i, d_j)])
    plt.show()
