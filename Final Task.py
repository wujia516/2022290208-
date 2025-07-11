# ----------------------------
# 基于大模型的情感语义分析
# ----------------------------

# 一、判断真假新闻 Prompt 模板
def generate_fact_check_prompt(title):
    return f"""You are a senior fact-checking expert. Based on the language, tone, and logic of the headline, decide whether it's real or fake.

Headline: {title}

Answer: Real / Fake

Reason: ...
"""

# 二、情感分析 Prompt 模板
def generate_sentiment_prompt(title):
    return f"""Read the news headline below and determine its sentiment as one of: Positive, Negative, or Neutral.

Headline: {title}

Sentiment: ...
Reason: ...
"""

# 三、结合情感信息判断真假新闻 Prompt
def generate_combined_prompt(title, sentiment):
    return f"""As a media analyst, determine whether the following headline is true or fake. Consider the tone, content, and emotional polarity.

Headline: {title}

Sentiment: {sentiment}

Answer: Real / Fake

Reason: ...
"""

# BERT + GPT 协同判断 Prompt 模板
def generate_bert_gpt_prompt(title, bert_result):
    return f"""You are an expert news analyst. The BERT model has preliminarily judged the following headline as {bert_result}.
Now, based on your own reasoning and the information from BERT, make a final judgment.

Headline: {title}

Answer: Real / Fake

Reason: ...
"""

# BERT + GPT + 情感语义分析 Prompt 模板
def generate_bert_gpt_sentiment_prompt(title, bert_result, sentiment):
    return f"""You are an expert news analyst. The BERT model preliminarily marked this headline as {bert_result}.
The sentiment analysis suggests the emotional tone is {sentiment}.
Based on this information and your own reasoning, determine whether the news is real or fake.

Headline: {title}

Sentiment: {sentiment}

Answer: Real / Fake

Reason: ...
"""

# ----------------------------
# 基于大模型的Twitter主题分析
# ----------------------------

# 一、数据准备
tweets = [
    "CDC Confirms New Breakthrough in Cancer Treatment",
    "Celebrity Found Dead in Apartment - Suicide Note Revealed",
    "NASA Launches Satellite to Monitor Global Warming",
    "Drinking Lemon Water Cures Diabetes, Experts Say",
    "Local Community Hosts Charity Drive for Homeless",
    "New Miracle Pill Helps You Lose 30 Pounds in a Week!",
    "President Signs Historic Climate Change Accord",
    "Bill Gates: Aliens Are Among Us and Watching Closely",
    "Community Volunteers Organize Free Health Clinic",
    "Study Shows New Drug Can Cure Rare Disease"
]

# 二、数据预处理
import re
import nltk
from nltk.corpus import stopwords
from nltk.stem import WordNetLemmatizer

nltk.download('stopwords')
nltk.download('wordnet')

stop_words = set(stopwords.words('english'))
lemmatizer = WordNetLemmatizer()

def preprocess(text):
    text = re.sub(r'[^a-zA-Z]', ' ', text).lower()
    tokens = text.split()
    tokens = [lemmatizer.lemmatize(word) for word in tokens if word not in stop_words and len(word) > 2]
    return tokens

processed_tweets = [preprocess(tweet) for tweet in tweets]

# 三、模型构建与训练
from gensim import corpora, models

dictionary = corpora.Dictionary(processed_tweets)
corpus = [dictionary.doc2bow(text) for text in processed_tweets]
lda_model = models.LdaModel(corpus=corpus, id2word=dictionary, num_topics=3, passes=10)

# 四、可视化分析
import pyLDAvis
import pyLDAvis.gensim_models

pyLDAvis.enable_notebook()
vis = pyLDAvis.gensim_models.prepare(lda_model, corpus, dictionary)
# pyLDAvis.show(vis)  # 在Jupyter中使用

# 2. 词云图
from wordcloud import WordCloud
import matplotlib.pyplot as plt

for t in range(3):
    plt.figure()
    plt.imshow(WordCloud().fit_words(dict(lda_model.show_topic(t, 10))))
    plt.axis("off")
    plt.title(f"Topic {t}")
    plt.show()

# 3. 热力图
import seaborn as sns
import pandas as pd

topic_dist = [lda_model.get_document_topics(doc, minimum_probability=0) for doc in corpus]
topic_df = pd.DataFrame([[prob for _, prob in doc] for doc in topic_dist])
sns.heatmap(topic_df, annot=True, cmap="YlGnBu")
plt.title("Document-Topic Distribution")
plt.xlabel("Topic")
plt.ylabel("Document")
plt.show()

# ----------------------------
# 基于多模态情感语义分析与预测模型
# ----------------------------

import torch
import torch.nn as nn
import torch.optim as optim
from transformers import BertTokenizer, BertModel
from torchvision import models, transforms
from torch.utils.data import DataLoader, Dataset
import numpy as np
from PIL import Image
import matplotlib.pyplot as plt

# 设置设备
device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')

# 1. BERT文本特征提取器
class BERTTextModel(nn.Module):
    def __init__(self, pretrained_model_name="bert-base-uncased"):
        super(BERTTextModel, self).__init__()
        self.bert = BertModel.from_pretrained(pretrained_model_name)
        self.fc = nn.Linear(self.bert.config.hidden_size, 256)  # 投影到256维

    def forward(self, input_ids, attention_mask):
        outputs = self.bert(input_ids, attention_mask=attention_mask)
        hidden_states = outputs[1]  # [CLS]的输出
        x = self.fc(hidden_states)
        return x

# 2. 图像特征提取器（使用预训练的ResNet50）
class ImageFeatureExtractor(nn.Module):
    def __init__(self):
        super(ImageFeatureExtractor, self).__init__()
        self.resnet = models.resnet50(pretrained=True)  # 预训练ResNet50
        self.resnet.fc = nn.Identity()  # 去掉最后的全连接层
        self.fc = nn.Linear(2048, 256)  # 投影到256维

    def forward(self, x):
        x = self.resnet(x)
        x = self.fc(x)
        return x

# 3. 跨模态注意力机制
class CrossModalAttention(nn.Module):
    def __init__(self, input_size=256):
        super(CrossModalAttention, self).__init__()
        self.attn_fc_text = nn.Linear(input_size, input_size)
        self.attn_fc_image = nn.Linear(input_size, input_size)

    def forward(self, text_features, image_features):
        text_weighted = torch.softmax(self.attn_fc_text(text_features), dim=-1)
        image_weighted = torch.softmax(self.attn_fc_image(image_features), dim=-1)

        fused_features = text_weighted * text_features + image_weighted * image_features
        return fused_features

# 4. 综合预测模型
class MultiModalPredictor(nn.Module):
    def __init__(self):
        super(MultiModalPredictor, self).__init__()
        self.text_model = BERTTextModel()
        self.image_model = ImageFeatureExtractor()
        self.attn_module = CrossModalAttention()
        self.fc = nn.Linear(256, 2)  # 2分类任务

    def forward(self, input_ids, attention_mask, image_tensor):
        text_features = self.text_model(input_ids, attention_mask)
        image_features = self.image_model(image_tensor)

        fused_features = self.attn_module(text_features, image_features)

        output = self.fc(fused_features)
        return output

# 5. 数据加载（假设有文本和图像数据）
class MultiModalDataset(Dataset):
    def __init__(self, texts, images, labels, tokenizer, transform=None):
        self.texts = texts
        self.images = images
        self.labels = labels
        self.tokenizer = tokenizer
        self.transform = transform

    def __len__(self):
        return len(self.texts)

    def __getitem__(self, idx):
        text = self.texts[idx]
        image = Image.open(self.images[idx])
        label = self.labels[idx]

        encoding = self.tokenizer(text, truncation=True, padding='max_length', max_length=128, return_tensors='pt')
        input_ids = encoding['input_ids'].squeeze(0)
        attention_mask = encoding['attention_mask'].squeeze(0)

        if self.transform:
            image = self.transform(image)

        return input_ids, attention_mask, image, label

# 6. 模型训练与评估
def train_model(model, train_loader, criterion, optimizer):
    model.train()
    running_loss = 0.0
    for input_ids, attention_mask, image, labels in train_loader:
        input_ids, attention_mask, image, labels = input_ids.to(device), attention_mask.to(device), image.to(device), labels.to(device)

        optimizer.zero_grad()
        outputs = model(input_ids, attention_mask, image)
        loss = criterion(outputs, labels)
        loss.backward()
        optimizer.step()

        running_loss += loss.item()

    return
