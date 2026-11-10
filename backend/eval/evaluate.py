"""
DocuSense AI evaluation runner
Usage:
  python evaluate.py --predictions system_results.csv --out results
Input predictions CSV columns:
  case_id, predicted_label, confidence, processing_ms, extracted_statement_ids, evidence_valid
Allowed labels:
  CONTRADICTION, SCOPE_DIFFERENCE, TEMPORAL_CHANGE, DEPENDENCY_CONFLICT,
  ENTAILED, NEUTRAL, NEEDS_REVIEW

Metrics:
- Classification accuracy, macro precision/recall/F1
- Contradiction precision, recall, F1 and false-positive rate
- Extraction precision/recall when extraction output is provided
- Mean / median / p95 processing latency
- Consistency score = 100 * (1 - normalized contradiction false-positive rate)
  This is an internal presentation indicator, not a standard scientific metric.
"""
import argparse, os, json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

LABELS = ["CONTRADICTION","SCOPE_DIFFERENCE","TEMPORAL_CHANGE","DEPENDENCY_CONFLICT","ENTAILED","NEUTRAL","NEEDS_REVIEW"]
CONTRA = {"CONTRADICTION","DEPENDENCY_CONFLICT"}

def safe_div(a,b):
    return float(a/b) if b else 0.0

def confusion(y_true, y_pred, labels):
    m = np.zeros((len(labels),len(labels)), dtype=int)
    idx={v:i for i,v in enumerate(labels)}
    for a,b in zip(y_true,y_pred):
        if a in idx and b in idx: m[idx[a],idx[b]] += 1
    return m

def classification_metrics(y_true,y_pred,labels):
    cm=confusion(y_true,y_pred,labels)
    per=[]
    for i,l in enumerate(labels):
        tp=cm[i,i]; fp=cm[:,i].sum()-tp; fn=cm[i,:].sum()-tp
        p=safe_div(tp,tp+fp); r=safe_div(tp,tp+fn); f=safe_div(2*p*r,p+r)
        per.append((l,p,r,f,int(cm[i,:].sum())))
    return cm,per

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--benchmark",default="benchmark_pairs.csv")
    ap.add_argument("--predictions",default="system_results.csv")
    ap.add_argument("--out",default="evaluation_output")
    ap.add_argument("--extraction",default=None,help="Optional CSV with case_id, expected_extracted, extracted")
    args=ap.parse_args()
    os.makedirs(args.out,exist_ok=True)
    gold=pd.read_csv(args.benchmark)
    pred=pd.read_csv(args.predictions)
    data=gold.merge(pred,on="case_id",how="left")
    data["predicted_label"]=data["predicted_label"].fillna("NEEDS_REVIEW").str.upper()
    y=data.gold_label.str.upper().tolist(); yp=data.predicted_label.tolist()
    cm,per=classification_metrics(y,yp,LABELS)
    accuracy=float(np.mean(np.array(y)==np.array(yp)))
    per_df=pd.DataFrame(per,columns=["label","precision","recall","f1","support"])
    per_df.to_csv(os.path.join(args.out,"per_class_metrics.csv"),index=False)
    pd.DataFrame(cm,index=LABELS,columns=LABELS).to_csv(os.path.join(args.out,"confusion_matrix.csv"))

    # Binary operational view: is this an actionable conflict?
    yt=np.array([v in CONTRA for v in y],dtype=bool)
    yp_bin=np.array([v in CONTRA for v in yp],dtype=bool)
    tp=int(np.sum(yt & yp_bin)); fp=int(np.sum(~yt & yp_bin))
    tn=int(np.sum(~yt & ~yp_bin)); fn=int(np.sum(yt & ~yp_bin))
    contradiction_precision=safe_div(tp,tp+fp)
    contradiction_recall=safe_div(tp,tp+fn)
    contradiction_f1=safe_div(2*contradiction_precision*contradiction_recall,contradiction_precision+contradiction_recall)
    fpr=safe_div(fp,fp+tn)
    lat=pd.to_numeric(data.get("processing_ms",pd.Series(dtype=float)),errors="coerce").dropna().to_numpy()
    latency={"count":int(len(lat)),"mean_ms":float(np.mean(lat)) if len(lat) else None,
             "median_ms":float(np.median(lat)) if len(lat) else None,
             "p95_ms":float(np.percentile(lat,95)) if len(lat) else None}
    consistency=max(0.0,100.0*(1.0-fpr))
    metrics={"cases":len(data),"accuracy":accuracy,"macro_precision":float(per_df.precision.mean()),
             "macro_recall":float(per_df.recall.mean()),"macro_f1":float(per_df.f1.mean()),
             "contradiction_tp":tp,"contradiction_fp":fp,"contradiction_tn":tn,"contradiction_fn":fn,
             "contradiction_precision":contradiction_precision,"contradiction_recall":contradiction_recall,
             "contradiction_f1":contradiction_f1,"false_positive_rate":fpr,
             "consistency_indicator_percent":consistency,"latency":latency}
    if args.extraction:
        ex=pd.read_csv(args.extraction)
        if {"expected_extracted","extracted"}.issubset(ex.columns):
            et=ex.expected_extracted.astype(bool).to_numpy(); ep=ex.extracted.astype(bool).to_numpy()
            metrics["extraction_precision"]=safe_div(int(np.sum(et&ep)),int(np.sum(ep)))
            metrics["extraction_recall"]=safe_div(int(np.sum(et&ep)),int(np.sum(et)))
            metrics["extraction_f1"]=safe_div(2*metrics["extraction_precision"]*metrics["extraction_recall"],
                                                metrics["extraction_precision"]+metrics["extraction_recall"])
    with open(os.path.join(args.out,"metrics.json"),"w") as f: json.dump(metrics,f,indent=2)

    # Confusion matrix plot
    fig,ax=plt.subplots(figsize=(10,8))
    im=ax.imshow(cm,aspect="auto")
    ax.set_xticks(range(len(LABELS)),LABELS,rotation=45,ha="right")
    ax.set_yticks(range(len(LABELS)),LABELS)
    ax.set_xlabel("Predicted label"); ax.set_ylabel("Gold label"); ax.set_title("DocuSense AI — Confusion Matrix")
    for i in range(len(LABELS)):
        for j in range(len(LABELS)): ax.text(j,i,str(cm[i,j]),ha="center",va="center")
    fig.colorbar(im,ax=ax); fig.tight_layout(); fig.savefig(os.path.join(args.out,"confusion_matrix.png"),dpi=180); plt.close(fig)

    # Category breakdown from benchmark actual labels
    cat=gold.gold_label.value_counts().sort_values(ascending=False)
    fig,ax=plt.subplots(figsize=(10,5)); cat.plot(kind="bar",ax=ax)
    ax.set_title("Benchmark Category Breakdown"); ax.set_xlabel("Gold category"); ax.set_ylabel("Number of test pairs")
    ax.tick_params(axis="x",rotation=35); fig.tight_layout()
    fig.savefig(os.path.join(args.out,"category_breakdown.png"),dpi=180); plt.close(fig)

    # Metric dashboard chart
    names=["Accuracy","Macro F1","Contradiction Precision","Contradiction Recall","Consistency indicator"]
    vals=[accuracy,metrics["macro_f1"],contradiction_precision,contradiction_recall,consistency/100]
    fig,ax=plt.subplots(figsize=(9,5)); bars=ax.bar(names,np.array(vals)*100)
    ax.set_ylim(0,100); ax.set_ylabel("Percent"); ax.set_title("DocuSense AI — Evaluation Metrics")
    ax.tick_params(axis="x",rotation=20)
    for b,v in zip(bars,vals): ax.text(b.get_x()+b.get_width()/2,b.get_height()+1,f"{v*100:.1f}%",ha="center")
    fig.tight_layout(); fig.savefig(os.path.join(args.out,"evaluation_metrics.png"),dpi=180); plt.close(fig)

    if len(lat):
        fig,ax=plt.subplots(figsize=(8,4)); ax.hist(lat,bins=min(15,max(5,len(lat)//2)))
        ax.set_title("Processing Latency Distribution"); ax.set_xlabel("Milliseconds per case"); ax.set_ylabel("Frequency")
        fig.tight_layout(); fig.savefig(os.path.join(args.out,"latency_distribution.png"),dpi=180); plt.close(fig)
    print(json.dumps(metrics,indent=2))

if __name__=="__main__": main()
