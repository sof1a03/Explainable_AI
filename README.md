# Explanable_AI
Explainable AI (INFOMXAI)

-----
Description of the DATASET
# Dowload: 
https://www.kaggle.com/datasets/ashery/chexpert/data

# Columns:

## Metadata

- **Path**  
  - **Description:** File path to the chest X-ray image.  
  - **Type:** String  
  - **Example:** `CheXpert-v1.0-small/train/patient12345/study1/view1_frontal.jpg`  

- **Sex**  
  - **Description:** Patient's biological sex.  
  - **Type:** Categorical (`Male`, `Female`)  
  - **Example:** `Male`  

- **Age**  
  - **Description:** Age of the patient at the time of the X-ray examination.  
  - **Type:** Integer  
  - **Example:** `57`  

- **Frontal/Lateral**  
  - **Description:** View of the chest X-ray image.  
  - **Type:** Categorical (`Frontal`, `Lateral`)  
  - **Example:** `Frontal`  

- **AP/PA**  
  - **Description:** Anterior-Posterior (AP) or Posterior-Anterior (PA) orientation of the X-ray image.  
  - **Type:** Categorical (`AP`, `PA`, or empty for Lateral views)  
  - **Example:** `AP`  

---

## Pathology Labels (1, 0, or -1)
- **Description:** Binary or uncertain labels for the presence of various chest pathologies or conditions.  
- **Type:** Categorical (`1` for positive, `0` for negative, `-1` for uncertain)  

---

- **No Finding**  
  - **Description:** Indicates whether the X-ray shows no observable abnormalities.  
  - **Type:** Binary (`1`, `0`)  

- **Enlarged Cardiomediastinum**  
  - **Description:** Enlargement of the mediastinal region, which may indicate heart or vascular disease.  
  - **Type:** Binary (`1`, `0`, `-1`)  

- **Cardiomegaly**  
  - **Description:** Enlargement of the heart.  
  - **Type:** Binary (`1`, `0`, `-1`)  

- **Lung Opacity**  
  - **Description:** Increased density in the lungs, potentially indicating fluid or other pathologies (e.g., pneumonia).  
  - **Type:** Binary (`1`, `0`, `-1`)  

- **Lung Lesion**  
  - **Description:** Presence of nodules, masses, or other abnormalities in the lung tissue.  
  - **Type:** Binary (`1`, `0`, `-1`)  

- **Edema**  
  - **Description:** Accumulation of excess fluid in the lungs.  
  - **Type:** Binary (`1`, `0`, `-1`)  

- **Consolidation**  
  - **Description:** Region of lung tissue filled with liquid instead of air, often due to pneumonia or other infections.  
  - **Type:** Binary (`1`, `0`, `-1`)  

- **Pneumonia**  
  - **Description:** Lung infection that inflames the air sacs, causing them to fill with fluid.  
  - **Type:** Binary (`1`, `0`, `-1`)  

- **Atelectasis**  
  - **Description:** Partial or complete collapse of a lung or lobe of the lung.  
  - **Type:** Binary (`1`, `0`, `-1`)  

- **Pneumothorax**  
  - **Description:** Collection of air in the pleural cavity, leading to lung collapse.  
  - **Type:** Binary (`1`, `0`, `-1`)  

- **Pleural Effusion**  
  - **Description:** Accumulation of fluid in the pleural space.  
  - **Type:** Binary (`1`, `0`, `-1`)  

- **Pleural Other**  
  - **Description:** Other abnormalities related to the pleura (lining of the lungs).  
  - **Type:** Binary (`1`, `0`, `-1`)  

- **Fracture**  
  - **Description:** Presence of bone fractures within the chest cavity or surrounding regions.  
  - **Type:** Binary (`1`, `0`, `-1`)  

- **Support Devices**  
  - **Description:** Indication of medical devices visible in the X-ray, such as pacemakers, catheters, or ventilators.  
  - **Type:** Binary (`1`, `0`, `-1`)  
