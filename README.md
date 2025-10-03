# Galileo - Open-Source Social Media Platform

<div align="center">
  
[![Python](https://img.shields.io/badge/Python-94.6%25-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://github.com/abdelbar472/galileo_open_sorce)
[![HTML](https://img.shields.io/badge/HTML-5.4%25-E34F26?style=for-the-badge&logo=html5&logoColor=white)](https://github.com/abdelbar472/galileo_open_sorce)
[![License](https://img.shields.io/badge/License-MIT-green?style=for-the-badge)](LICENSE)
  
</div>

## 🚀 Overview

Galileo is a comprehensive open-source social media and collaboration platform built with Django. It combines social networking features with team collaboration tools, enabling communities to connect, communicate, and collaborate in real-time.

![Galileo Platform](https://github.com/abdelbar472/galileo_open_sorce/raw/main/docs/assets/banner.png)

## ✨ Key Features

- **Real-time Chat**: Instant messaging using WebSockets via Django Channels
- **Social Networking**: Posts, likes, comments, and user profiles
- **Community Spaces**: Create and join topic-based communities
- **Team Collaboration**: Tools for team management and project coordination
- **Rich Media Support**: Share photos, videos, and documents
- **Robust Authentication**: JWT, social auth, and role-based access control

## 🛠️ Tech Stack

| Component | Technology |
|-----------|------------|
| Backend Framework | Python / Django |
| Real-time Communication | Django Channels |
| Database | SQLite (Dev) / ScyllaDB (Prod) |
| Caching | Redis |
| Containerization | Docker / Kubernetes |
| CI/CD | GitHub Actions |

## 📋 Requirements

- Python 3.8+
- Django 4.0+
- Redis
- Docker (optional)

## 🔧 Installation & Setup

### Local Development Setup

1. **Clone the repository**
   ```bash
   git clone https://github.com/abdelbar472/galileo_open_sorce.git
   cd galileo_open_sorce
   ```

2. **Create and activate virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment variables**
   ```bash
   cp .env.example .env
   # Edit .env file with your configuration
   ```

5. **Run migrations**
   ```bash
   python manage.py migrate
   ```

6. **Create a superuser**
   ```bash
   python manage.py createsuperuser
   ```

7. **Start the development server**
   ```bash
   python manage.py runserver
   ```

### Docker Setup

```bash
docker-compose up -d
```

## 🧪 Testing

```bash
python manage.py test
```

## 📚 Documentation

Comprehensive documentation is available in the [docs](docs/) directory or visit our [Wiki](https://github.com/abdelbar472/galileo_open_sorce/wiki).

## 🤝 Contributing

Contributions are welcome! Please check out our [Contributing Guidelines](CONTRIBUTING.md) to get started.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🔍 For Recruiters

Galileo demonstrates my capabilities in:

- **Full-Stack Development**: Python/Django backend with HTML/CSS frontend
- **Real-time Communication**: Implementing WebSockets for instant messaging
- **Database Design**: Complex data relationships and efficient querying
- **DevOps**: Containerization and CI/CD pipeline setup
- **Security**: Authentication, authorization, and secure data handling
- **Scalable Architecture**: Designed for horizontal scaling with Kubernetes

## 📱 Contact

Have questions or want to discuss this project further? Feel free to reach out:

- GitHub: [@abdelbar472](https://github.com/abdelbar472)
- Email: [your-email@example.com]

---

<div align="center">
  
⭐ Star this repo if you find it useful! ⭐
  
</div>
