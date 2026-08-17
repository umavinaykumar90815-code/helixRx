import numpy as np
from sklearn.ensemble import RandomForestClassifier

class VariantImpactPredictor:
    """
    Machine Learning model trained to classify unannotated novel genetic 
    variants as Pathogenic (Functional Loss) or Tolerated (Normal Function).
    """
    def __init__(self):
        self.model = RandomForestClassifier(n_estimators=100, random_state=42)
        self._train_synthetic_baseline()
        
    def _train_synthetic_baseline(self):
        # Synthetic training dataset representing genomic impact metrics:
        # Features: [CADD_Score (0-60), PolyPhen_Score (0-1), SIFT_Score (0-1), Phylop_Conservation (-2 to 10)]
        X_train = np.array([
            [35.0, 0.95, 0.01, 7.5],  # Pathogenic
            [42.0, 0.99, 0.00, 8.2],  # Pathogenic
            [28.0, 0.88, 0.03, 6.1],  # Pathogenic
            [ 5.2, 0.05, 0.85, 0.2],  # Tolerated
            [ 8.1, 0.12, 0.72, -0.5], # Tolerated
            [ 2.0, 0.01, 0.98, 0.0],  # Tolerated
            [31.0, 0.91, 0.02, 5.8],  # Pathogenic
            [12.0, 0.20, 0.45, 1.1]   # Tolerated
        ])
        
        # Labels: 1 = Pathogenic / Loss-of-Function, 0 = Tolerated / Normal
        y_train = np.array([1, 1, 1, 0, 0, 0, 1, 0])
        self.model.fit(X_train, y_train)

    def predict_variant_impact(self, cadd_score, polyphen_score, sift_score, phylop_score):
        features = np.array([[cadd_score, polyphen_score, sift_score, phylop_score]])
        prediction = self.model.predict(features)[0]
        confidence = np.max(self.model.predict_proba(features)) * 100
        
        status = "Pathogenic / Functional Loss" if prediction == 1 else "Tolerated / Benign"
        return {
            "prediction": status,
            "confidence": f"{confidence:.1f}%",
            "is_loss_of_function": bool(prediction == 1)
        }

if __name__ == "__main__":
    predictor = VariantImpactPredictor()
    
    # Test novel unannotated variant query
    res = predictor.predict_variant_impact(cadd_score=33.5, polyphen_score=0.92, sift_score=0.01, phylop_score=6.4)
    print("\n--- ML NOVEL VARIANT PREDICTION ---")
    print(f"Predicted Impact: {res['prediction']}")
    print(f"Model Confidence: {res['confidence']}")