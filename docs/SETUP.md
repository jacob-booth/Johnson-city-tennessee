# Setting Up Johnson City Guide Automation

## GitHub Secrets Configuration

To enable automatic updates, you need to configure the following secrets in your GitHub repository:

1. Go to your repository's Settings
2. Navigate to Secrets and Variables > Actions
3. Add the following secrets:

- `YELP_API_KEY`: Your Yelp Fusion API key
- `EVENTBRITE_API_KEY`: Your Eventbrite API key
- `NPS_API_KEY`: Your National Park Service API key
- `OPENWEATHER_API_KEY`: Your OpenWeather API key
- `ASTRONOMY_API_KEY`: Your Astronomy API key

## Getting API Keys

### Yelp API
1. Visit [Yelp Fusion](https://www.yelp.com/developers)
2. Create an app to get your API key

### Eventbrite API
1. Visit [Eventbrite API](https://www.eventbrite.com/platform/)
2. Create an app to get your API key

### National Park Service API
1. Visit [NPS Developer Resources](https://www.nps.gov/subjects/developer/)
2. Sign up for an API key

### OpenWeather API
1. Visit [OpenWeather](https://openweathermap.org/api)
2. Sign up for a free account
3. Get your API key

### Astronomy API
1. Visit [Farmsense API](https://farmsense.net/api/)
2. Sign up for an API key

## Local Development

For local development:

1. Copy `.env.example` to `.env`
2. Add your API keys to the `.env` file
3. Never commit the `.env` file to version control

## Security Notes

- Keep your API keys secure and never commit them to the repository
- Use environment variables for local development
- Use GitHub Secrets for automated workflows
- Regularly rotate your API keys for better security

## Automatic Updates

The guide automatically updates:
- Daily at 1:00 AM EST
- Weather updates hourly
- Moon phase updates daily
- Agricultural data updates daily

All updates are committed and pushed automatically via GitHub Actions.