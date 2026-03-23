# Building Permit Compliance Portal Frontend

This is the **React-based frontend** for the Building Permit Compliance Portal, a modern web application designed for residents to navigate the permit process with AI assistance.

## Features
- **Dashboard:** Overview of property and permit application status.
- **Permit Submission:** Interactive flow for creating permit applications and uploading building plan PDFs.
- **AI Analysis Viewer:** Visualizes structured results from the Compliance Agent, highlighting approved elements and specific code violations.
- **Interactive Chat:** An integrated modal to ask conversational follow-up questions about non-compliance issues.
- **Property Management:** Add and manage property locations for permit applications.
- **Modern UI:** Built using **TailwindCSS** and follows the **"Architectural Authority"** design system (Intentional Asymmetry, Tonal Layering, Glass & Gradient effects).

## Tech Stack
- **Framework:** React + Vite + TypeScript
- **Styling:** TailwindCSS + Lucide-React (icons)
- **State Management:** Zustand
- **API Client:** Axios

## Local Development

### Prerequisites
- Node.js 18+ (with `npm`)
- API Gateway running (on `localhost:8080` by default).

### Setup and Execution
1.  **Install dependencies:**
    ```bash
    make install
    ```
2.  **Start the development server:**
    ```bash
    make start
    ```
    The application will be available at `http://localhost:5173`.

## Deployment

The frontend is containerized and ready for deployment to **Google Cloud Run** using Cloud Build.

```bash
make deploy
```

This builds the production assets using Vite and serves them through a lightweight production-ready server (as defined in the `Dockerfile`).
