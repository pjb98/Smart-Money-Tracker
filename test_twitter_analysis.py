"""
Test script for Twitter Account Analysis
Demonstrates how to analyze Twitter accounts linked to Pumpfun tokens
"""
import asyncio
import json
from src.ingestion.twitter_analyzer import TwitterAnalyzer
from config import settings


async def test_twitter_analysis():
    """Test the Twitter analyzer with example accounts"""

    print("=" * 70)
    print("TWITTER ACCOUNT ANALYZER - TEST")
    print("=" * 70)

    # Initialize analyzer
    analyzer = TwitterAnalyzer(bearer_token=settings.twitter_bearer_token)

    # Test cases - various Twitter URL formats
    test_cases = [
        {
            'name': 'Direct URL (twitter.com)',
            'data': {'twitter': 'https://twitter.com/solana'}
        },
        {
            'name': 'Direct URL (x.com)',
            'data': {'x': 'https://x.com/ethereum'}
        },
        {
            'name': 'Handle with @ symbol',
            'data': {'twitter': '@bitcoin'}
        },
        {
            'name': 'Plain handle',
            'data': {'twitter': 'opensea'}
        },
    ]

    for test_case in test_cases:
        print(f"\n{'='*70}")
        print(f"TEST: {test_case['name']}")
        print(f"{'='*70}")

        try:
            # Extract handle
            username = analyzer.extract_twitter_handle(test_case['data'])

            if not username:
                print("❌ Could not extract Twitter handle")
                continue

            print(f"✅ Extracted handle: @{username}")

            # Perform comprehensive analysis
            print(f"\nAnalyzing @{username}...")
            analysis = await analyzer.comprehensive_analysis(username)

            # Display results
            print(f"\n{'='*70}")
            print("ANALYSIS RESULTS")
            print(f"{'='*70}")

            print(f"\n📊 Overall Assessment:")
            print(f"   Risk Score: {analysis.get('risk_score', 'N/A')}/10")
            print(f"   Risk Level: {analysis.get('risk_level', 'N/A')}")

            if analysis.get('limited_data'):
                print(f"\n⚠️  Limited data available (no Twitter API key or rate limit)")
                print(f"   Twitter URL: {analysis.get('twitter_url', 'N/A')}")
                continue

            # Account info
            account_info = analysis.get('account_info', {})
            print(f"\n👤 Account Information:")
            print(f"   Username: @{analysis.get('username', 'N/A')}")
            print(f"   Verified: {'✅ Yes' if account_info.get('verified') else '❌ No'}")

            # Age analysis
            age_analysis = analysis.get('age_analysis', {})
            print(f"\n📅 Account Age:")
            print(f"   Age: {age_analysis.get('account_age_days', 0)} days")
            print(f"   New Account: {'⚠️ Yes' if age_analysis.get('is_new_account') else '✅ No'}")
            print(f"   Very New: {'🚨 Yes' if age_analysis.get('is_very_new_account') else '✅ No'}")

            # Follower analysis
            follower_analysis = analysis.get('follower_analysis', {})
            print(f"\n👥 Follower Metrics:")
            print(f"   Followers: {follower_analysis.get('followers_count', 0):,}")
            print(f"   Following: {follower_analysis.get('following_count', 0):,}")
            print(f"   Ratio: {follower_analysis.get('follower_following_ratio', 0):.2f}")

            # Engagement analysis
            engagement_analysis = analysis.get('engagement_analysis', {})
            print(f"\n💬 Engagement:")
            print(f"   Tweets Analyzed: {engagement_analysis.get('total_tweets_analyzed', 0)}")
            print(f"   Avg Engagement: {engagement_analysis.get('avg_engagement_rate', 0):.1f} per tweet")
            print(f"   Low Engagement: {'⚠️ Yes' if engagement_analysis.get('low_engagement') else '✅ No'}")

            # Tweet frequency
            frequency_analysis = analysis.get('frequency_analysis', {})
            print(f"\n📈 Tweet Frequency:")
            print(f"   Tweets/Day: {frequency_analysis.get('tweets_per_day', 0):.1f}")
            print(f"   Bot Behavior: {'🚨 Suspicious' if frequency_analysis.get('excessive_tweet_frequency') else '✅ Normal'}")

            # Sentiment
            sentiment_analysis = analysis.get('sentiment_analysis', {})
            print(f"\n😊 Sentiment:")
            print(f"   Avg Polarity: {sentiment_analysis.get('avg_sentiment_polarity', 0):.2f}")
            print(f"   Positive Ratio: {sentiment_analysis.get('positive_tweet_ratio', 0):.1%}")
            print(f"   Label: {sentiment_analysis.get('sentiment_label', 'N/A')}")

            # Key insights
            if analysis.get('insights'):
                print(f"\n💡 Key Insights:")
                for insight in analysis['insights']:
                    print(f"   {insight}")

            # Save full analysis to file
            output_file = f"data/twitter_analysis_{username}.json"
            with open(output_file, 'w') as f:
                json.dump(analysis, f, indent=2, default=str)
            print(f"\n💾 Full analysis saved to: {output_file}")

        except Exception as e:
            print(f"❌ Error: {e}")
            import traceback
            traceback.print_exc()

    # Cleanup
    await analyzer.close()

    print(f"\n{'='*70}")
    print("TEST COMPLETE")
    print(f"{'='*70}")


async def test_token_integration():
    """Test Twitter analysis as part of token analysis flow"""
    print("\n\n" + "=" * 70)
    print("INTEGRATION TEST: Token with Twitter Account")
    print("=" * 70)

    # Simulate a token from Pump.fun with social links
    mock_token_data = {
        'address': 'MockToken123xyz',
        'symbol': 'MOCK',
        'name': 'Mock Token',
        'twitter': 'https://twitter.com/solana',  # Example Twitter
        'telegram': 'https://t.me/mocktoken',
        'website': 'https://mocktoken.com'
    }

    print(f"\nToken: {mock_token_data['name']} ({mock_token_data['symbol']})")
    print(f"Twitter: {mock_token_data['twitter']}")

    # Analyze Twitter account
    analyzer = TwitterAnalyzer(bearer_token=settings.twitter_bearer_token)

    try:
        username = analyzer.extract_twitter_handle(mock_token_data)
        if username:
            print(f"\nAnalyzing Twitter account: @{username}...")
            analysis = await analyzer.comprehensive_analysis(username, mock_token_data)

            print(f"\n✅ Analysis Complete!")
            print(f"   Risk Score: {analysis.get('risk_score', 'N/A')}/10")
            print(f"   Risk Level: {analysis.get('risk_level', 'N/A')}")

            # This is what would be passed to feature engineering
            print(f"\n📊 Features that would be extracted:")
            print(f"   twitter_has_account: 1")
            print(f"   twitter_verified: {1 if analysis.get('account_info', {}).get('verified') else 0}")
            print(f"   twitter_followers: {analysis.get('follower_analysis', {}).get('followers_count', 0)}")
            print(f"   twitter_risk_score: {analysis.get('risk_score', 5.0)}")
            print(f"   twitter_account_age_days: {analysis.get('age_analysis', {}).get('account_age_days', 0)}")
        else:
            print("❌ Could not extract Twitter handle")

    finally:
        await analyzer.close()

    print(f"\n{'='*70}")
    print("INTEGRATION TEST COMPLETE")
    print(f"{'='*70}")


async def main():
    """Run all tests"""
    print("\n")
    print("╔" + "═" * 68 + "╗")
    print("║" + " " * 15 + "TWITTER ANALYZER TEST SUITE" + " " * 25 + "║")
    print("╚" + "═" * 68 + "╝")

    # Check if Twitter API is configured
    if settings.twitter_bearer_token:
        print("\n✅ Twitter API configured - Full testing mode")
    else:
        print("\n⚠️  No Twitter API key - Testing with fallback mode")
        print("   Set TWITTER_BEARER_TOKEN in .env for full functionality")

    # Run tests
    await test_twitter_analysis()
    await test_token_integration()

    print("\n\n🎉 All tests complete!")
    print("\nNext steps:")
    print("  1. Set TWITTER_BEARER_TOKEN in .env for full API access")
    print("  2. Run the real-time monitor: python monitor_realtime.py")
    print("  3. Twitter analysis will automatically run for each migration")
    print()


if __name__ == "__main__":
    asyncio.run(main())
