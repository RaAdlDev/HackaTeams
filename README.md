# HackaTeams

HackaTeams is a networking and collaboration ecosystem designed to connect developers, creators, and innovators. Whether you are building a squad for an upcoming hackathon or seeking a co-founder for a startup, HackaTeams matches you with the right talent based on skills, objectives, and availability.

## Features

*   **Smart Matching:** Tinder-style developer and project discovery based on shared tags (abilities, expertise, objectives).
*   **Formal Applications:** Structured join requests detailing weekly hours, time zone, expected rewards, and a project improvement pitch.
*   **Comprehensive Portfolios:** Showcase past hackathons, previous projects, and future goals on your personal profile.
*   **Real-Time Chat:** Connect instantly with potential teammates via WebSocket-powered messaging.
*   **Social Feed:** An "ads" section to broadcast project ideas and recruit talent.
*   **Secure In-App Payments:** Integrated Stripe and PayPal processing for seamless, secure project compensation.

## Tech Stack

*   **Backend:** Python, FastAPI, SQLAlchemy, PostgreSQL, WebSockets
*   **Frontend:** React.js
*   **Payments:** Stripe API, PayPal API
*   **Infrastructure:** Docker, Docker Compose

## Getting Started

### Prerequisites
*   Node.js & npm
*   Python 3.10+
*   Docker & Docker Compose
*   PostgreSQL

### Backend Setup
1. Clone the repository: `git clone https://github.com/yourusername/HackaTeams.git`
2. Navigate to the backend directory: `cd backend`
3. Create a virtual environment: `python -m venv venv` and activate it.
4. Install dependencies: `pip install -r requirements.txt`
5. Set up your `.env` file with your Database URL, JWT Secret, and Stripe/PayPal keys.
6. Run database migrations: `alembic upgrade head`
7. Start the server: `uvicorn main:app --reload`
*(Alternatively, run `docker-compose up --build` to spin up the API and Database together).*

### Frontend Setup
1. Navigate to the frontend directory: `cd frontend`
2. Install dependencies: `npm install`
3. Configure your `.env` file with the backend API URL.
4. Start the development server: `npm start`

