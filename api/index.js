import express from 'express';
import cors from 'cors';
import axios from 'axios';
import * as dotenv from 'dotenv';

dotenv.config();

// API Keys from environment variables
const YELP_API_KEY = process.env.YELP_API_KEY;
const EVENTBRITE_API_KEY = process.env.EVENTBRITE_API_KEY;
const NPS_API_KEY = process.env.NPS_API_KEY;

if (!YELP_API_KEY || !EVENTBRITE_API_KEY || !NPS_API_KEY) {
    throw new Error('Required API keys not found in environment variables');
}

// API endpoints
const API_ENDPOINTS = {
    yelp: 'https://api.yelp.com/v3/businesses/search',
    eventbrite: 'https://www.eventbriteapi.com/v3/events/search/',
    nps: 'https://developer.nps.gov/api/v1/parks'
};

const app = express();
app.use(cors());
app.use(express.json());

// Search restaurants
app.get('/api/restaurants', async (req, res) => {
    try {
        const { term, limit = 20 } = req.query;
        const response = await axios.get(API_ENDPOINTS.yelp, {
            headers: {
                Authorization: `Bearer ${YELP_API_KEY}`,
            },
            params: {
                location: 'Johnson City, TN',
                categories: 'restaurants',
                term,
                limit: Math.min(limit, 50),
            },
        });
        res.json(response.data.businesses);
    } catch (error) {
        console.error('Yelp API error:', error.response?.data || error.message);
        res.status(500).json({ error: 'Failed to fetch restaurants' });
    }
});

// Search shops
app.get('/api/shops', async (req, res) => {
    try {
        const { term, limit = 20 } = req.query;
        const response = await axios.get(API_ENDPOINTS.yelp, {
            headers: {
                Authorization: `Bearer ${YELP_API_KEY}`,
            },
            params: {
                location: 'Johnson City, TN',
                categories: 'shopping',
                term,
                limit: Math.min(limit, 50),
            },
        });
        res.json(response.data.businesses);
    } catch (error) {
        console.error('Yelp API error:', error.response?.data || error.message);
        res.status(500).json({ error: 'Failed to fetch shops' });
    }
});

// Search events
app.get('/api/events', async (req, res) => {
    try {
        const { q, start_date } = req.query;
        
        // First get the organization ID
        const orgResponse = await axios.get('https://www.eventbriteapi.com/v3/users/me/organizations/', {
            headers: {
                Authorization: `Bearer ${EVENTBRITE_API_KEY}`,
            },
        });

        if (!orgResponse.data.organizations || orgResponse.data.organizations.length === 0) {
            return res.json([]);
        }

        const orgId = orgResponse.data.organizations[0].id;

        // Then search for events within that organization
        const response = await axios.get(`https://www.eventbriteapi.com/v3/organizations/${orgId}/events/`, {
            headers: {
                Authorization: `Bearer ${EVENTBRITE_API_KEY}`,
            },
            params: {
                q,
                start_date: {
                    range_start: start_date,
                },
                status: 'live',
            },
        });

        res.json(response.data.events || []);
    } catch (error) {
        console.error('Eventbrite API error:', error.response?.data || error.message);
        res.json([]); // Return empty array on error to maintain compatibility
    }
});

// Get parks
app.get('/api/parks', async (req, res) => {
    try {
        const { limit = 10 } = req.query;
        const response = await axios.get(API_ENDPOINTS.nps, {
            headers: {
                'X-Api-Key': NPS_API_KEY,
            },
            params: {
                stateCode: 'TN',
                q: 'Johnson City',
                limit,
            },
        });
        res.json(response.data.data);
    } catch (error) {
        console.error('NPS API error:', error.response?.data || error.message);
        res.status(500).json({ error: 'Failed to fetch parks' });
    }
});

// Error handling middleware
app.use((err, req, res, next) => {
    console.error(err.stack);
    res.status(500).json({ error: 'Something went wrong!' });
});

const PORT = process.env.PORT || 3000;
app.listen(PORT, () => {
    console.log(`Johnson City API server running on port ${PORT}`);
});
