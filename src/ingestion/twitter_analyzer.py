"""
Twitter Account Analyzer for Token Social Analysis
Analyzes Twitter accounts linked to Pumpfun tokens to detect legitimacy, engagement, and red flags
"""
import aiohttp
import asyncio
import re
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from loguru import logger
from textblob import TextBlob


class TwitterAnalyzer:
    """
    Comprehensive Twitter account analyzer for token social signals

    Analyzes:
    - Account age and legitimacy
    - Follower count and growth patterns
    - Tweet frequency and engagement
    - Sentiment analysis
    - Bot detection and red flags
    - Influencer connections
    """

    def __init__(self, bearer_token: Optional[str] = None):
        """
        Initialize Twitter analyzer

        Args:
            bearer_token: Twitter API v2 Bearer Token (optional for free tier)
        """
        self.bearer_token = bearer_token
        self.session: Optional[aiohttp.ClientSession] = None
        self.api_base = "https://api.twitter.com/2"

        # Red flag thresholds
        self.NEW_ACCOUNT_DAYS = 30  # Account created < 30 days ago
        self.LOW_ENGAGEMENT_THRESHOLD = 0.01  # < 1% engagement rate
        self.SUSPICIOUS_FOLLOWER_RATIO = 10  # Following >> Followers
        self.BOT_TWEET_FREQUENCY = 50  # > 50 tweets/day

        logger.info("Initialized Twitter analyzer")

    async def _ensure_session(self):
        """Ensure HTTP session exists"""
        if self.session is None or self.session.closed:
            headers = {}
            if self.bearer_token:
                headers["Authorization"] = f"Bearer {self.bearer_token}"
            self.session = aiohttp.ClientSession(headers=headers)

    async def close(self):
        """Close HTTP session"""
        if self.session and not self.session.closed:
            await self.session.close()

    def extract_twitter_handle(self, social_data: Dict[str, Any]) -> Optional[str]:
        """
        Extract Twitter handle from Pumpfun social data

        Args:
            social_data: Social links from token metadata

        Returns:
            Twitter handle (without @) or None
        """
        try:
            # Check different possible formats
            twitter_url = (
                social_data.get('twitter') or
                social_data.get('twitter_url') or
                social_data.get('x') or
                social_data.get('x_url')
            )

            if not twitter_url:
                return None

            # Extract handle from URL
            # Examples:
            # - https://twitter.com/username
            # - https://x.com/username
            # - @username
            # - username

            if isinstance(twitter_url, str):
                # Remove http/https
                twitter_url = re.sub(r'https?://', '', twitter_url)
                # Remove domain
                twitter_url = re.sub(r'(twitter\.com|x\.com)/', '', twitter_url)
                # Remove @ symbol
                twitter_url = twitter_url.lstrip('@')
                # Remove trailing slash and query params
                twitter_url = twitter_url.split('/')[0].split('?')[0]

                return twitter_url if twitter_url else None

            return None

        except Exception as e:
            logger.error(f"Error extracting Twitter handle: {e}")
            return None

    async def get_account_info(self, username: str) -> Optional[Dict[str, Any]]:
        """
        Fetch Twitter account information using API v2

        Args:
            username: Twitter handle (without @)

        Returns:
            Account info dict or None
        """
        if not self.bearer_token:
            logger.warning("No Twitter bearer token - using fallback analysis")
            return await self._fallback_account_analysis(username)

        try:
            await self._ensure_session()

            url = f"{self.api_base}/users/by/username/{username}"
            params = {
                "user.fields": "created_at,description,public_metrics,verified,profile_image_url"
            }

            async with self.session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    return data.get('data')
                elif response.status == 429:
                    logger.warning("Twitter API rate limit exceeded")
                    return None
                else:
                    logger.warning(f"Failed to fetch account info: {response.status}")
                    return None

        except Exception as e:
            logger.error(f"Error fetching account info for @{username}: {e}")
            return None

    async def _fallback_account_analysis(self, username: str) -> Optional[Dict[str, Any]]:
        """
        Fallback analysis without Twitter API (scraping or basic checks)

        Args:
            username: Twitter handle

        Returns:
            Basic account info
        """
        # This is a placeholder - in production, you could:
        # 1. Use a web scraper (nitter.net, etc.)
        # 2. Use third-party APIs (RapidAPI Twitter endpoints)
        # 3. Return minimal info for now

        logger.debug(f"Using fallback analysis for @{username}")

        return {
            'username': username,
            'fallback_mode': True,
            'twitter_url': f"https://twitter.com/{username}"
        }

    async def get_recent_tweets(
        self,
        user_id: str,
        max_results: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Fetch recent tweets from a user

        Args:
            user_id: Twitter user ID
            max_results: Number of tweets to fetch (max 100 for free tier)

        Returns:
            List of tweet dicts
        """
        if not self.bearer_token:
            return []

        try:
            await self._ensure_session()

            url = f"{self.api_base}/users/{user_id}/tweets"
            params = {
                "max_results": min(max_results, 100),
                "tweet.fields": "created_at,public_metrics,referenced_tweets"
            }

            async with self.session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    return data.get('data', [])
                else:
                    logger.warning(f"Failed to fetch tweets: {response.status}")
                    return []

        except Exception as e:
            logger.error(f"Error fetching tweets for user {user_id}: {e}")
            return []

    def analyze_account_age(self, created_at: str) -> Dict[str, Any]:
        """
        Analyze account age and flag if suspiciously new

        Args:
            created_at: ISO format creation date

        Returns:
            Age analysis dict
        """
        try:
            created_date = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
            age_days = (datetime.now(created_date.tzinfo) - created_date).days
            age_hours = age_days * 24

            is_new = age_days < self.NEW_ACCOUNT_DAYS
            is_very_new = age_days < 7

            return {
                'account_age_days': age_days,
                'account_age_hours': age_hours,
                'is_new_account': is_new,
                'is_very_new_account': is_very_new,
                'created_at': created_at,
                'red_flag': is_very_new  # Very new accounts are suspicious for new tokens
            }

        except Exception as e:
            logger.error(f"Error analyzing account age: {e}")
            return {
                'account_age_days': 0,
                'red_flag': True
            }

    def analyze_followers(self, public_metrics: Dict[str, int]) -> Dict[str, Any]:
        """
        Analyze follower metrics and detect suspicious patterns

        Args:
            public_metrics: Twitter public metrics (followers, following, tweets, etc.)

        Returns:
            Follower analysis dict
        """
        followers = public_metrics.get('followers_count', 0)
        following = public_metrics.get('following_count', 0)
        tweets = public_metrics.get('tweet_count', 0)

        # Calculate ratios
        follower_following_ratio = followers / following if following > 0 else 0
        tweets_per_follower = tweets / followers if followers > 0 else 0

        # Detect suspicious patterns
        suspicious_ratio = following > followers * self.SUSPICIOUS_FOLLOWER_RATIO
        very_low_followers = followers < 100
        no_tweets = tweets == 0

        return {
            'followers_count': followers,
            'following_count': following,
            'tweet_count': tweets,
            'follower_following_ratio': follower_following_ratio,
            'tweets_per_follower': tweets_per_follower,
            'low_follower_count': very_low_followers,
            'suspicious_following_ratio': suspicious_ratio,
            'no_tweets_flag': no_tweets,
            'red_flag': suspicious_ratio or (very_low_followers and not no_tweets)
        }

    def analyze_tweet_engagement(self, tweets: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Analyze tweet engagement patterns

        Args:
            tweets: List of recent tweets

        Returns:
            Engagement analysis dict
        """
        if not tweets:
            return {
                'avg_engagement_rate': 0,
                'total_tweets_analyzed': 0,
                'red_flag': True
            }

        total_likes = 0
        total_retweets = 0
        total_replies = 0

        for tweet in tweets:
            metrics = tweet.get('public_metrics', {})
            total_likes += metrics.get('like_count', 0)
            total_retweets += metrics.get('retweet_count', 0)
            total_replies += metrics.get('reply_count', 0)

        num_tweets = len(tweets)
        avg_likes = total_likes / num_tweets
        avg_retweets = total_retweets / num_tweets
        avg_replies = total_replies / num_tweets

        total_engagement = total_likes + total_retweets + total_replies
        avg_engagement_rate = total_engagement / num_tweets

        # Low engagement is a red flag
        low_engagement = avg_engagement_rate < 10  # Less than 10 total engagements per tweet

        return {
            'total_tweets_analyzed': num_tweets,
            'avg_likes_per_tweet': avg_likes,
            'avg_retweets_per_tweet': avg_retweets,
            'avg_replies_per_tweet': avg_replies,
            'avg_engagement_rate': avg_engagement_rate,
            'total_engagement': total_engagement,
            'low_engagement': low_engagement,
            'red_flag': low_engagement and num_tweets > 10
        }

    def analyze_tweet_frequency(self, tweets: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Analyze tweet frequency to detect bot behavior

        Args:
            tweets: List of recent tweets

        Returns:
            Frequency analysis dict
        """
        if not tweets:
            return {
                'tweets_per_day': 0,
                'red_flag': False
            }

        # Calculate time range
        dates = []
        for tweet in tweets:
            created_at = tweet.get('created_at')
            if created_at:
                date = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                dates.append(date)

        if len(dates) < 2:
            return {
                'tweets_per_day': 0,
                'red_flag': True
            }

        dates.sort()
        time_span_days = (dates[-1] - dates[0]).total_seconds() / 86400

        if time_span_days == 0:
            time_span_days = 1

        tweets_per_day = len(tweets) / time_span_days

        # Very high frequency suggests bot
        is_bot_frequency = tweets_per_day > self.BOT_TWEET_FREQUENCY

        return {
            'tweets_per_day': tweets_per_day,
            'time_span_days': time_span_days,
            'excessive_tweet_frequency': is_bot_frequency,
            'red_flag': is_bot_frequency
        }

    def analyze_tweet_sentiment(self, tweets: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Analyze sentiment of recent tweets

        Args:
            tweets: List of recent tweets

        Returns:
            Sentiment analysis dict
        """
        if not tweets:
            return {
                'avg_sentiment_polarity': 0,
                'avg_sentiment_subjectivity': 0,
                'positive_tweet_ratio': 0
            }

        sentiments = []
        subjectivities = []

        for tweet in tweets:
            text = tweet.get('text', '')
            if text:
                try:
                    blob = TextBlob(text)
                    sentiments.append(blob.sentiment.polarity)
                    subjectivities.append(blob.sentiment.subjectivity)
                except:
                    pass

        if not sentiments:
            return {
                'avg_sentiment_polarity': 0,
                'avg_sentiment_subjectivity': 0,
                'positive_tweet_ratio': 0
            }

        avg_polarity = sum(sentiments) / len(sentiments)
        avg_subjectivity = sum(subjectivities) / len(subjectivities)
        positive_ratio = len([s for s in sentiments if s > 0]) / len(sentiments)

        return {
            'avg_sentiment_polarity': avg_polarity,
            'avg_sentiment_subjectivity': avg_subjectivity,
            'positive_tweet_ratio': positive_ratio,
            'sentiment_label': 'positive' if avg_polarity > 0.1 else ('negative' if avg_polarity < -0.1 else 'neutral')
        }

    async def comprehensive_analysis(
        self,
        username: str,
        token_metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Perform comprehensive Twitter account analysis

        Args:
            username: Twitter handle
            token_metadata: Optional token metadata from Pumpfun

        Returns:
            Complete analysis dict with risk scores
        """
        logger.info(f"Analyzing Twitter account: @{username}")

        analysis = {
            'username': username,
            'twitter_url': f"https://twitter.com/{username}",
            'analyzed_at': datetime.now().isoformat()
        }

        # Get account info
        account_info = await self.get_account_info(username)

        if not account_info or account_info.get('fallback_mode'):
            logger.warning(f"Limited data available for @{username}")
            analysis['limited_data'] = True
            analysis['risk_score'] = 5  # Neutral risk without data
            return analysis

        analysis['account_info'] = account_info

        # Analyze account age
        if 'created_at' in account_info:
            age_analysis = self.analyze_account_age(account_info['created_at'])
            analysis['age_analysis'] = age_analysis

        # Analyze followers
        if 'public_metrics' in account_info:
            follower_analysis = self.analyze_followers(account_info['public_metrics'])
            analysis['follower_analysis'] = follower_analysis

        # Get and analyze tweets
        user_id = account_info.get('id')
        if user_id and self.bearer_token:
            tweets = await self.get_recent_tweets(user_id, max_results=100)

            if tweets:
                analysis['tweet_count_analyzed'] = len(tweets)
                analysis['engagement_analysis'] = self.analyze_tweet_engagement(tweets)
                analysis['frequency_analysis'] = self.analyze_tweet_frequency(tweets)
                analysis['sentiment_analysis'] = self.analyze_tweet_sentiment(tweets)

        # Calculate overall risk score
        risk_score = self._calculate_risk_score(analysis)
        analysis['risk_score'] = risk_score
        analysis['risk_level'] = self._get_risk_level(risk_score)

        # Generate summary insights
        analysis['insights'] = self._generate_insights(analysis)

        logger.info(f"Twitter analysis complete for @{username}: Risk={risk_score}/10")

        return analysis

    def _calculate_risk_score(self, analysis: Dict[str, Any]) -> float:
        """
        Calculate overall risk score (0-10, higher = more risky)

        Args:
            analysis: Complete analysis dict

        Returns:
            Risk score from 0-10
        """
        risk = 0.0

        # Age factors (max 3 points)
        age_analysis = analysis.get('age_analysis', {})
        if age_analysis.get('is_very_new_account'):
            risk += 3.0
        elif age_analysis.get('is_new_account'):
            risk += 1.5

        # Follower factors (max 3 points)
        follower_analysis = analysis.get('follower_analysis', {})
        if follower_analysis.get('suspicious_following_ratio'):
            risk += 2.0
        if follower_analysis.get('low_follower_count'):
            risk += 1.0

        # Engagement factors (max 2 points)
        engagement_analysis = analysis.get('engagement_analysis', {})
        if engagement_analysis.get('low_engagement'):
            risk += 2.0

        # Frequency factors (max 2 points)
        frequency_analysis = analysis.get('frequency_analysis', {})
        if frequency_analysis.get('excessive_tweet_frequency'):
            risk += 2.0

        # Verification bonus (reduce risk)
        account_info = analysis.get('account_info', {})
        if account_info.get('verified'):
            risk = max(0, risk - 2.0)

        return min(10.0, risk)

    def _get_risk_level(self, risk_score: float) -> str:
        """Get risk level label from score"""
        if risk_score <= 3:
            return "LOW"
        elif risk_score <= 6:
            return "MEDIUM"
        else:
            return "HIGH"

    def _generate_insights(self, analysis: Dict[str, Any]) -> List[str]:
        """
        Generate human-readable insights from analysis

        Args:
            analysis: Complete analysis dict

        Returns:
            List of insight strings
        """
        insights = []

        # Account age insights
        age_analysis = analysis.get('age_analysis', {})
        if age_analysis.get('is_very_new_account'):
            insights.append(f"⚠️ Account is very new ({age_analysis.get('account_age_days')} days old)")
        elif age_analysis.get('is_new_account'):
            insights.append(f"⚠️ Account is relatively new ({age_analysis.get('account_age_days')} days old)")
        else:
            insights.append(f"✅ Established account ({age_analysis.get('account_age_days', 0)} days old)")

        # Follower insights
        follower_analysis = analysis.get('follower_analysis', {})
        followers = follower_analysis.get('followers_count', 0)
        if followers > 10000:
            insights.append(f"✅ Strong following ({followers:,} followers)")
        elif followers > 1000:
            insights.append(f"🔶 Moderate following ({followers:,} followers)")
        else:
            insights.append(f"⚠️ Low following ({followers:,} followers)")

        # Engagement insights
        engagement_analysis = analysis.get('engagement_analysis', {})
        avg_engagement = engagement_analysis.get('avg_engagement_rate', 0)
        if avg_engagement > 50:
            insights.append(f"✅ High engagement ({avg_engagement:.1f} avg per tweet)")
        elif avg_engagement > 10:
            insights.append(f"🔶 Moderate engagement ({avg_engagement:.1f} avg per tweet)")
        else:
            insights.append(f"⚠️ Low engagement ({avg_engagement:.1f} avg per tweet)")

        # Verification
        account_info = analysis.get('account_info', {})
        if account_info.get('verified'):
            insights.append("✅ Verified account")

        # Bot detection
        frequency_analysis = analysis.get('frequency_analysis', {})
        if frequency_analysis.get('excessive_tweet_frequency'):
            insights.append("⚠️ Suspicious posting frequency (possible bot)")

        return insights


# Helper function for easy integration
async def analyze_token_twitter(
    token_social_data: Dict[str, Any],
    bearer_token: Optional[str] = None
) -> Optional[Dict[str, Any]]:
    """
    Quick helper to analyze Twitter for a token

    Args:
        token_social_data: Social data from Pumpfun token
        bearer_token: Twitter API bearer token

    Returns:
        Twitter analysis dict or None
    """
    analyzer = TwitterAnalyzer(bearer_token)

    try:
        username = analyzer.extract_twitter_handle(token_social_data)

        if not username:
            logger.info("No Twitter account found for token")
            return None

        analysis = await analyzer.comprehensive_analysis(username)
        return analysis

    finally:
        await analyzer.close()


# Example usage
async def example():
    """Test the analyzer"""
    import json

    # Example: Analyze a token's Twitter account
    token_social_data = {
        'twitter': 'https://twitter.com/solana'  # Example
    }

    # Use Twitter bearer token if available
    bearer_token = None  # Set to your token

    analysis = await analyze_token_twitter(token_social_data, bearer_token)

    if analysis:
        print(json.dumps(analysis, indent=2, default=str))
        print(f"\nRisk Score: {analysis['risk_score']}/10 ({analysis['risk_level']})")
        print("\nInsights:")
        for insight in analysis['insights']:
            print(f"  {insight}")


if __name__ == "__main__":
    asyncio.run(example())
