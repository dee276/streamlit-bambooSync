# 📊 LXT BambooSync

**LXT BambooSync** est une application Streamlit conçue pour automatiser la réconciliation des données de performance et le suivi de présence en temps réel pour les équipes de LXT à Montréal et à l'international.

L'outil connecte l'API de **BambooHR** avec les données d'extraction de vitesse (CSV) pour fournir une vision claire de la productivité et de l'utilisation des ressources.

## 🚀 Fonctionnalités

*   **Présence Live :** Visualisez instantanément qui est "Clocked in" via l'API BambooHR.
*   **Analyse de Performance :** Calcul automatique de l'Utilisation et de la Productivité par employé.
*   **Gestion Multi-Équipes :** Supporte plusieurs configurations d'équipes (Montréal, Lao, etc.) via un fichier de mapping dynamique.
*   **Persistance de Session :** Le mot de passe et le fichier CSV chargé restent en mémoire pendant toute la durée de la session.
*   **Interface Responsive :** Tableaux formatés avec précision (2 décimales) et indicateurs visuels de statut.

## 🛠️ Installation et Configuration

### 1. Prérequis
* Python 3.9+
* Un compte BambooHR avec accès à l'API.

### 2. Installation locale
```bash
# Cloner le dépôt
git clone [https://github.com/votre-utilisateur/lxt-bamboosync.git](https://github.com/votre-utilisateur/lxt-bamboosync.git)
cd lxt-bamboosync

# Installer les dépendances
pip install -r requirements.txt
