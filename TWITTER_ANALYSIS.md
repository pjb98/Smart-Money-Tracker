# Twitter Account Analysis for Pumpfun Tokens

## Overview

The Twitter Account Analyzer is a comprehensive module that analyzes Twitter accounts linked to Pumpfun tokens to assess legitimacy, engagement, and potential red flags. This helps predict token performance by evaluating the social credibility of the project.

## Features

### 1. Account Age Analysis
- Detects newly created accounts (< 30 days old)
- Flags very new accounts (< 7 days old) as suspicious
- Provides account age in days and hours

### 2. Follower Metrics
- Analyzes follower count and following count
- Calculates follower/following ratio
- Detects suspicious patterns (e.g., following >> followers)
- Flags low follower counts

### 3. Engagement Analysis
- Fetches and analyzes recent tweets (up to 100)
- Calculates average likes, retweets, and replies per tweet
- Computes overall engagement rate
- Detects low engagement (potential fake accounts)

### 4. Bot Detection
- Analyzes tweet frequency
- Detects excessive posting (>50 tweets/day)
- Identifies suspicious automation patterns

### 5. Sentiment Analysis
- Analyzes sentiment of recent tweets using TextBlob
- Provides polarity score (-1 to +1)
- Calculates positive tweet ratio
- Labels overall sentiment (positive/neutral/negative)

### 6. Risk Scoring
- Comprehensive risk score (0-10, higher = more risky)
- Based on multiple factors:
  - Account age (max 3 points)
  - Follower patterns (max 3 points)
  - Engagement levels (max 2 points)
  - Bot behavior (max 2 points)
  - Verification bonus (-2 points)
- Risk levels: LOW (0-3), MEDIUM (4-6), HIGH (7-10)

## Setup

### 1. Twitter API Access (Optional but Recommended)

To get full functionality, you need a Twitter API Bearer Token:

1. Go to [Twitter Developer Portal](https://developer.twitter.com/)
2. Create a new app or use an existing one
3. Get your Bearer Token from the app dashboard
4. Add to your `.env` file:

```env
TWITTER_BEARER_TOKEN=your_bearer_token_here
```

**Note:** The analyzer works in fallback mode without API access, but provides limited data.

### 2. Install Dependencies

The Twitter analyzer uses TextBlob for sentiment analysis:

```bash
pip install textblob
```

Or install all dependencies:

```bash
pip install -r requirements.txt
```

## Usage

### Standalone Analysis

Test the Twitter analyzer independently:

```bash
python test_twitter_analysis.py
```

This will:
- Test various Twitter URL formats
- Analyze example accounts
- Show comprehensive analysis results
- Save results to JSON files

### Integrated Analysis

The Twitter analyzer is automatically integrated into the main agent:

1. **Real-time monitoring:**
```bash
python monitor_realtime.py
```

When a migration is detected, the system will:
- Extract Twitter handle from token metadata
- Analyze the account comprehensively
- Include results in feature engineering
- Pass insights to Claude AI for deeper analysis

2. **Single token analysis:**
```bash
python main.py
```

## API Integration

### Extracting Twitter Handle

```python
from src.ingestion.twitter_analyzer import TwitterAnalyzer

analyzer = TwitterAnalyzer(bearer_token=your_token)

# Supports multiple formats
token_data = {
    'twitter': 'https://twitter.com/username'  # or
    # 'twitter': '@username'  # or
    # 'twitter': 'username'  # or
    # 'x': 'https://x.com/username'
}

username = analyzer.extract_twitter_handle(token_data)
```

### Comprehensive Analysis

```python
analysis = await analyzer.comprehensive_analysis(username, token_metadata)

# Returns:
{
    'username': 'solana',
    'risk_score': 2.0,
    'risk_level': 'LOW',
    'account_info': {...},
    'age_analysis': {...},
    'follower_analysis': {...},
    'engagement_analysis': {...},
    'frequency_analysis': {...},
    'sentiment_analysis': {...},
    'insights': [...]
}
```

## Features Added to ML Pipeline

The Twitter analyzer adds **20+ features** to the feature engineering pipeline:

### Account Features
- `twitter_has_account` - Binary flag (1 if account exists)
- `twitter_account_age_days` - Age in days
- `twitter_account_is_new` - Flagged if < 30 days
- `twitter_account_is_very_new` - Flagged if < 7 days

### Follower Features
- `twitter_followers` - Follower count
- `twitter_following` - Following count
- `twitter_follower_ratio` - Followers/Following ratio
- `twitter_low_followers` - Flagged if < 100 followers
- `twitter_suspicious_following` - Flagged if following >> followers

### Engagement Features
- `twitter_avg_engagement` - Average engagement per tweet
- `twitter_low_engagement` - Flagged if very low
- `twitter_tweets_analyzed` - Number of tweets analyzed

### Bot Detection Features
- `twitter_tweets_per_day` - Average tweets per day
- `twitter_excessive_frequency` - Flagged if > 50/day

### Sentiment Features
- `twitter_account_sentiment` - Avg sentiment polarity (-1 to +1)
- `twitter_positive_ratio` - Ratio of positive tweets

### Verification & Risk
- `twitter_verified` - Binary flag for verified accounts
- `twitter_risk_score` - Overall risk score (0-10)

## Risk Factors

### High Risk Indicators (🚨)
- Very new account (< 7 days old)
- Low follower count (< 100)
- Suspicious following ratio (following >> followers)
- Very low engagement on tweets
- Excessive tweet frequency (bot behavior)

### Medium Risk Indicators (⚠️)
- Relatively new account (< 30 days)
- Moderate follower count (100-1000)
- Low but not absent engagement

### Low Risk Indicators (✅)
- Established account (> 30 days)
- Strong follower base (> 1000)
- Good engagement rates
- Verified account
- Normal posting frequency

## Integration with Claude AI

Twitter analysis results are automatically passed to Claude AI for deeper insights. Claude considers:

1. **Social credibility** - Is the Twitter account legitimate?
2. **Community engagement** - Does the account have real engagement?
3. **Red flags** - Are there suspicious patterns?
4. **Overall legitimacy** - How does Twitter presence correlate with other signals?

Claude combines Twitter analysis with:
- Wallet intelligence (whale detection, insider analysis)
- Pre-migration metrics (bonding curve data)
- On-chain activity
- Phanes scan data

## Example Output

```
Twitter Analysis Results:
  - Account: @exampletoken
  - Risk Score: 4.5/10 (MEDIUM)

💡 Key Insights:
  ⚠️ Account is relatively new (23 days old)
  🔶 Moderate following (856 followers)
  ✅ High engagement (127.3 avg per tweet)
  ✅ Verified account
```

## Fallback Mode

Without a Twitter API key, the analyzer operates in **fallback mode**:

- Can still extract Twitter handles from token metadata
- Returns basic account info (username, URL)
- Assigns neutral risk score (5/10)
- All Twitter features set to defaults

This ensures the system continues to work even without API access.

## Rate Limits

Twitter API Free Tier limits:
- **Tweet cap:** 1,500 tweets per month
- **Read requests:** Limited to 10,000/month

The analyzer is optimized to stay within these limits:
- Fetches max 100 recent tweets per analysis
- Includes fallback mode for rate limit errors
- Caches results where possible

## Best Practices

1. **Get Twitter API access** for full functionality
2. **Monitor rate limits** if analyzing many tokens
3. **Use fallback mode** as a safety net
4. **Combine with other signals** - Don't rely solely on Twitter
5. **Check insights** - The insights provide human-readable summaries

## Troubleshooting

### "No Twitter bearer token"
- Set `TWITTER_BEARER_TOKEN` in `.env` file
- System will use fallback mode without it

### "Twitter API rate limit exceeded"
- Wait for the rate limit to reset (monthly)
- Reduce analysis frequency
- Consider upgrading Twitter API tier

### "Could not extract Twitter handle"
- Verify token has Twitter link in metadata
- Check that URL format is correct
- Token may not have social links

## Future Enhancements

Potential improvements:
- [ ] Twitter API v2 full integration
- [ ] Historical tweet analysis (time series)
- [ ] Influencer network analysis
- [ ] Hashtag trend analysis
- [ ] Profile image/banner analysis (AI vision)
- [ ] Account activity patterns (posting times)
- [ ] Fake follower detection (advanced)

## Contributing

To improve Twitter analysis:
1. Test with various token types
2. Identify false positives/negatives
3. Suggest new red flag patterns
4. Improve sentiment analysis accuracy
5. Add new features to feature engineering

---

**Built for:** Pumpfun → Raydium Prediction Agent
**Module:** `src/ingestion/twitter_analyzer.py`
**Test Script:** `test_twitter_analysis.py`
