class RecommendationEngine:
    """
    Provides actionable recommendations based on detected fraud signals.

    This engine uses a simple rule-based mapping to link specific findings
    from the detection models to concrete, easy-to-understand advice for the user.
    The goal is to empower the user to take immediate, appropriate action to
    protect themselves.
    """
    def __init__(self):
        # A mapping from keywords found in model findings to recommendations.
        self.recommendation_map = {
            'scam': [
                "Do not respond to suspicious messages.",
                "Report the scam to relevant authorities."
            ],
            'phishing': [
                "Do not click on suspicious links.",
                "Verify the sender's identity before sharing personal information."
            ],
            'disposable email': [
                "Be cautious when dealing with users using disposable email addresses.",
                "Request a permanent email address for further communication."
            ],
            'high-risk keywords': [
                "Review the message for high-risk keywords and proceed with caution.",
                "Avoid sharing sensitive information."
            ],
            'deepfake': [
                "Verify the authenticity of audio or video messages.",
                "Do not trust media content without proper validation."
            ]
        }

    def get_recommendations(self, findings):
        """
        Generates a unique list of recommendations based on the findings.

        Args:
            findings (list): A list of finding dictionaries from the pipeline.

        Returns:
            list: A list of unique, relevant recommendation strings.
        """
        recos = set()
        
        if not findings:
            recos.add("Always be cautious with unsolicited communications.")
            return list(recos)

        for finding in findings:
            finding_text = (finding['model'] + ' ' + finding['finding']).lower()
            for keyword, reco_list in self.recommendation_map.items():
                if keyword in finding_text:
                    for reco in reco_list:
                        recos.add(reco)
        
        if not recos:
            recos.add("Review the detected signals carefully and proceed with caution.")

        return sorted(list(recos))