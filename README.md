# AquaSentinel AI
AquaSentinel is the final operational flood-monitoring dashboard built around the existing FloodML legacy model. The project keeps the original pickled model intact, loads it only in a compatible legacy Python/scikit-learn runtime, and wraps it in a transparent service layer that displays clearly when live data or forecast data are unavailable instead of inventing values.

## Features
- Flood risk prediction using the preserved legacy `model.pickle` artifact.
- OpenWeather-backed weather and forecast retrieval when an API key is configured.
- Advisory-only water-management recommendations with `Requires human/operator confirmation.` text.
- SQLite-backed alert and history logs for recent alerts and trend tracking.
- Rich AquaSentinel dashboard with historical risk chart, alert guidance, and status cards.
- Legacy prototype routes redirected to the final dashboard for a cleaner UX.

## Getting started
1. Use the legacy-compatible runtime for the model:
   - Python 3.8
   - scikit-learn 0.23.2
   - NumPy 1.19.5
2. Install dependencies from the project requirements file.
3. Paste your OpenWeather key into `OPENWEATHER_API_KEY` in `.env`. The Flask backend loads this file on startup; existing shell environment variables take precedence. Add optional SMTP settings there too if you want email alerts.
4. Run the app:
   - `python app.py`
5. Open `http://localhost:5000/`.

## Environment variables
- `OPENWEATHER_API_KEY` — required for live weather and forecast data.
- `SMTP_HOST` — SMTP host for alert emails.
- `SMTP_PORT` — SMTP port (default `587`).
- `SMTP_USERNAME` — SMTP username.
- `SMTP_PASSWORD` — SMTP password.
- `ALERT_EMAIL` — recipient email for alert messages.

After restarting Flask, check `/api/health` for `openweather_configured: true`; then check `/api/weather?location=Hyderabad` for `"weather":{"status":"ok"}` to confirm the key is accepted and live data is being returned.

## Model comparison
Run `python training/compare_models.py` with the model-compatible Python environment to train and compare six classifiers on `training/final_data.csv`. The script writes `model_comparison.csv` and `model_comparison.json` into the FloodML project folder; Flask serves the results at `/api/model-comparison`, and the React dashboard displays the metrics. This comparison does not replace or modify the deployed `model.pickle`. The data split is stratified 80/20; augmented examples may make scores higher than performance on independently collected data.

## Data policy
The application intentionally avoids fabricated values. If external weather or forecast data is unavailable, the UI and API surfaces return explicit messages such as `Data unavailable`, `Live weather temporarily unavailable.`, and `Forecast data unavailable.`

## Architecture
- `app.py` — Flask app, routes, alert persistence, prediction orchestration.
- `src/services/` — risk engine, weather service, forecast service, water-management logic.
- `src/notifications/` — email and notification management.
- `templates/index.html` — final dashboard UI.
- `aqua_sentinel.db` — local alert and history database.

## Notes on model compatibility
The model file shipped with the project is a legacy scikit-learn artifact. It is intentionally preserved and loaded without retraining. Newer Python/scikit-learn stacks may fail to deserialize it, so using the project’s compatible environment is recommended for reliable predictions.
We are extremely proud of compiling and creating a dataset that can accurately and effectively reflect the current situation of floods in India, as well as allow us to make future predictions. We are also proud to have expanded our machine learning skills by testing out new models, and ultimately implementing a model with over 98% accuracy. Lastly, we are proud to have integrated various data augmentation, data mining, and date manipulation techniques, together with our model, to create detailed and sophisticated, yet compelling and easy to understand plots for data visualization.

## What We learned
First and foremost, we learned a great amount of web scraping and data mining, through our collection of data from websites as well as API's. We also learned techniques to manipulate and augment that data to create more effective datasets that provide us with better visualizations. Since it was our team's first time using Plotly, we also learned how to use plotly chart studio to create great visualizations. Lastly, we also expanded our machine learning skills through the testing of various models, especially the random forest classification model.

## What's next for FloodML
We would like to expand our web application to cover cities in countries all around the world, and to make our visualizations and predictions accessible to people across all nations, in an effort to prepare people and governments to the best of their ability.

Our team also believes further scientific analysis of satellite data could help critically in flood detection. Thus, we would like to expand to create an image classification model to detect signs of upcoming floods from satellite images.

Most importantly, our team is proud to have created a web application that could potentially help people and governments prepare for and reallocate resources for floods, potentially saving thousands of lives and millions of livelihoods.
