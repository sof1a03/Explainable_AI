# Explanable_AI
Explainable AI (INFOMXAI)

-----
# Description of the DATASET

## Dowload: 
https://www.kaggle.com/datasets/ashery/chexpert/data

# Columns:

## Metadata

- **Path**: File path to the chest X-ray image. **Type:** String
    
- **Sex** : Patient's biological sex. **Type:** Categorical (`Male`, `Female`)  

- **Age** : Age of the patient at the time of the X-ray examination. **Type:** Integer 

- **Frontal/Lateral**: View of the chest X-ray image. **Type:** Categorical (`Frontal`, `Lateral`)  

- **AP/PA**:  Anterior-Posterior (AP) or Posterior-Anterior (PA) orientation of the X-ray image. **Type:** Categorical (`AP`, `PA`, or empty for Lateral views)  

---

## Pathology Labels (1, 0, or -1)
Binary or uncertain labels for the presence of various chest pathologies or conditions.  
**Type:** Categorical (`1` for positive, `0` for negative, `-1` for uncertain)  

- **No Finding** : Indicates whether the X-ray shows no observable abnormalities.  

- **Enlarged Cardiomediastinum**: Enlargement of the mediastinal region, which may indicate heart or vascular disease.   

- **Cardiomegaly**: Enlargement of the heart.  

- **Lung Opacity** : Increased density in the lungs, potentially indicating fluid or other pathologies (e.g., pneumonia).  

- **Lung Lesion** : Presence of nodules, masses, or other abnormalities in the lung tissue.  

- **Edema**: Accumulation of excess fluid in the lungs.  

- **Consolidation**: Region of lung tissue filled with liquid instead of air, often due to pneumonia or other infections.  

- **Pneumonia**: Lung infection that inflames the air sacs, causing them to fill with fluid.  

- **Atelectasis** : Partial or complete collapse of a lung or lobe of the lung.
    
- **Pneumothorax** : Collection of air in the pleural cavity, leading to lung collapse.  

- **Pleural Effusion**: Accumulation of fluid in the pleural space.  

- **Pleural Other**: Other abnormalities related to the pleura (lining of the lungs).  

- **Fracture**: Presence of bone fractures within the chest cavity or surrounding regions.  

- **Support Devices**: Indication of medical devices visible in the X-ray, such as pacemakers, catheters, or ventilators.  
