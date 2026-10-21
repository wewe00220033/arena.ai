"""Offline, exact-answer-only security dialogue solver. No cloud fallback."""
import re

LOCAL_SECURITY_CACHE = {'randomly selected for a prize': "No way! I'm reporting you to Jagex!", "logged in while i'm out of the room": 'No.', 'remove a hijacker': 'Use the Account Recovery System.', 'make you a player moderator': "Don't give them the information and send an 'Abuse report'.", 'watching a stream': "Report the stream as a scam. Real Jagex streams have a 'verified' mark.", 'do a difficult quest': "Don't give them my password.", 'who can i give my password': 'Nobody.', 'how do i set up two-factor': 'Through account settings on oldschool.runescape.com.', 'example of a good bank pin': 'The birthday of a famous person or event.', 'check your stats': "Don't give out your password to anyone. Not even close friends.", 'comment on the forum post': 'Report the player for phishing.', 'invitation via in- game chat or email': 'Report the incident and do not click any links.', 'how do i set a bank pin': 'Talk to any banker.', 'moderator asks me for my account details': "Politely tell them no, then use the 'Report Abuse' button.", 'after you answer the question': 'Read the text and follow the advice given.', 'prevent me from saying my pin': 'No.', 'that sound?': "No way! You'll just take my gold for your own! Reported!", 'verify my identity': "Delete it - it's a fake!", 'website claims': "Nothing, it's a fake.", 'react?': "Don't share your information and report the player.", 'make you a member for free': "Don't tell them anything and click the 'Report Abuse' button.", 'okay to buy an old school': 'No, you should never buy an account.', 'invitation via social media': 'Report the incident and do not click any links.', 'where is it safe': 'Only on the Old School RuneScape website.', 'best way to secure your account': 'Two-factor authentication on your account and your registered email.', 'share my account with': 'Nobody.', 'purchase items and/or gold': 'Do not visit the website and report the player who messaged you.', 'whose responsibility': 'Me.', 'someone to level your account': 'No, you should never allow anyone to use your account.', 'account is compromised': 'Secure my device and reset my password.', 'respond?': 'Decline the offer and report that player.', 'password backwards': "Don't type in my password backwards and report the player.", 'keylogger or virus': 'Virus scan my device then change my password.', 'registered email secure': 'Set up two-factor authentication with my email provider.', 'characteristic of a secure password': "It's never reused on other websites or accounts.", 'lose out! what do you say?': "Nope, you're tricking me into going somewhere dangerous.", 'not through responding to emails.': 'No.', 'authenticator': 'Through account settings', 'phishing': 'Report the player', 'giveaway': 'Report the incident and do not click any links.'}

def normalize(value):
    return re.sub(r"\s+", " ", value.strip().casefold()).rstrip(".!?")

def solve_security_dialogue(question, options):
    if not isinstance(question, str) or not question.strip():
        return None
    if not isinstance(options, list) or not all(isinstance(o, str) for o in options):
        return None
    answers = {normalize(a) for q, a in LOCAL_SECURITY_CACHE.items()
               if q.casefold() in question.casefold()}
    matches = [o for o in options if normalize(o) in answers]
    return matches[0] if len(matches) == 1 else None

select_best_answer = solve_security_dialogue
