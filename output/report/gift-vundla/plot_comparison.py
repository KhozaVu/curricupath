"""Plot the already audited common-subset observations without new model runs."""
from pathlib import Path
import json
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

OUT=Path(__file__).resolve().parent
data=json.loads((OUT/'report_evidence.json').read_text(encoding='utf8'))
levels=['low','medium','high']
arms=[('rules_only','Rules-only','black','--','s'),
      ('curricupath','CurricuPath','0.25','-','o'),
      ('handbook_rag','Grid RAG','0.50','-.','^'),
      ('structured_rules_llm','Rules LLM','0.15',':','D')]
plt.rcParams.update({'font.family':'serif','font.serif':['Times New Roman','DejaVu Serif'],'font.size':9,'pdf.fonttype':42,'axes.spines.top':False,'axes.spines.right':False})
fig,axes=plt.subplots(2,1,figsize=(3.23,2.72),sharex=True)
x=np.arange(3)
for arm,label,color,style,marker in arms:
    metrics=[data['metrics'][level][arm] for level in levels]
    assert all(m['n_cases']==40 for m in metrics)
    assert all(m['safety']['unsafe_false_positive_rate']['denominator']==26 for m in metrics)
    kw=dict(label=label,color=color,linestyle=style,marker=marker,markersize=4,linewidth=1.1,markerfacecolor='white' if arm!='curricupath' else color,markeredgewidth=.8)
    axes[0].plot(x,[m['macro_f1'] for m in metrics],**kw)
    axes[1].plot(x,[m['safety']['unsafe_false_positive_rate']['numerator'] for m in metrics],**kw)
for ax in axes:
    ax.set_xlim(-.17,2.17)
    ax.grid(axis='y',color='.86',lw=.45)
    ax.tick_params(labelsize=8)
axes[0].set_ylim(0,1.08);axes[0].set_yticks([0,.5,1]);axes[0].set_ylabel('Macro-F1',labelpad=5)
axes[1].set_ylim(-.5,10);axes[1].set_yticks([0,5,10]);axes[1].set_ylabel('Unsafe count',labelpad=5)
axes[1].set_xticks(x,['Code','Name','Informal']);axes[1].set_xlabel('Question wording',labelpad=2)
handles,labels=axes[0].get_legend_handles_labels()
fig.legend(handles,labels,loc='upper center',bbox_to_anchor=(.54,1.01),ncol=2,frameon=False,fontsize=8,columnspacing=1.2,handlelength=2.2)
fig.subplots_adjust(left=.18,right=.97,bottom=.15,top=.78,hspace=.23)
fig.savefig(OUT/'baseline_comparison.pdf',bbox_inches='tight',pad_inches=.04)
fig.savefig(OUT/'baseline_comparison.png',dpi=200,bbox_inches='tight',pad_inches=.04)
plt.close(fig)
print('Created baseline comparison from checked 40-case metrics; unsafe denominator 26 per wording.')
