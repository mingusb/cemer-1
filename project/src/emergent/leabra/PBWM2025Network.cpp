#include "PBWM2025Network.h"
#include "PBWM2025NetworkState_cpp.h"
#include "PBWM2025UnitSpec.h"
#include <LeabraLayer>
#include <LeabraLayerSpec>
#include <LeabraConSpec>
#include <LeabraConSpec_cpp>
#include <LeabraConState_cpp>
#include <LeabraPrjn>
#include <AllProjectionSpecs>
#include <QFile>
#include <QJsonArray>
#include <QJsonDocument>
#include <QJsonObject>
#include <taMisc>
#include <limits>
#include <vector>

TA_BASEFUNS_CTORS_DEFN(PBWM2025Network);
NetworkState_cpp* PBWM2025Network::NewNetworkState() const { return new PBWM2025NetworkState_cpp; }
TypeDef* PBWM2025Network::NetworkStateType() const { return &TA_PBWM2025NetworkState_cpp; }
namespace {
float number(const QJsonObject& o,const char* key) { return static_cast<float>(o[key].toDouble()); }
void inhib_parameters(LeabraInhibSpec& p,const QJsonObject& o) {
 p.on=o["On"].toBool(); p.gi=number(o,"Gi");p.ff=number(o,"FF");p.fb=number(o,"FB");
 p.fb_tau=number(o,"FBTau");p.max_vs_avg=number(o,"MaxVsAvg");p.ff0=number(o,"FF0");p.UpdateAfterEdit_NoGui();
}
void unit_parameters(PBWM2025UnitSpec& u,const QJsonObject& l) {
 const auto a=l["act"].toObject(),xx=a["XX1"].toObject(),dt=a["Dt"].toObject(),init=a["Init"].toObject();
 u.act.thr=number(xx,"Thr");u.act.gain=number(xx,"Gain");u.act.nvar=number(xx,"NVar");u.act.vm_act_thr=number(xx,"VmActThr");
 u.dt.integ=number(dt,"Integ");u.dt.vm_tau=number(dt,"VmTau");u.dt.net_tau=number(dt,"GTau");u.dt.fast_cyc=0;
 u.init.v_m=number(init,"Vm");u.init.act=number(init,"Act");u.init.netin=number(init,"Ge");
 const auto bars=a["Gbar"].toObject(),rev=a["Erev"].toObject();
 u.g_bar.e=number(bars,"E");u.g_bar.l=number(bars,"L");u.g_bar.i=number(bars,"I");u.g_bar.k=number(bars,"K");
 u.e_rev.e=number(rev,"E");u.e_rev.l=number(rev,"L");u.e_rev.i=number(rev,"I");u.e_rev.k=number(rev,"K");
 const auto opt=a["OptThresh"].toObject(),range=a["VmRange"].toObject(),clamp=a["Clamp"].toObject()["Range"].toObject();
 u.opt_thresh.send=number(opt,"Send");u.opt_thresh.delta=number(opt,"Delta");
 u.vm_range.min=number(range,"Min");u.vm_range.max=number(range,"Max");u.clamp_range.min=number(clamp,"Min");u.clamp_range.max=number(clamp,"Max");
 u.kna_adapt.on=false;u.deep.on=false;u.noise_type.type=LeabraNoiseSpec::NO_NOISE;
 const auto learn=l["learn"].toObject(),avg=learn["ActAvg"].toObject(),avgl=learn["AvgL"].toObject();
 u.act_misc.avg_init=number(avg,"Init");u.act_avg.ss_tau=number(avg,"SSTau");u.act_avg.s_tau=number(avg,"STau");u.act_avg.m_tau=number(avg,"MTau");
 u.act_avg.ru_lrn_m=number(avg,"LrnM");u.act_avg.su_lrn_m=number(avg,"LrnM");
 u.avg_l.init=number(avgl,"Init");u.avg_l.gain=number(avgl,"Gain");u.avg_l.min=number(avgl,"Min");u.avg_l.tau=number(avgl,"Tau");
 const QString type=l["type"].toString();
 if(type=="InputLayer") u.role=PBWM2025UnitSpec::INPUT;
 else if(type=="TargetLayer") u.role=PBWM2025UnitSpec::TARGET;
 else if(type=="MatrixLayer") u.role=PBWM2025UnitSpec::MATRIX;
 else if(type=="GPiThalLayer") u.role=PBWM2025UnitSpec::GPI;
 else if(type=="PFCDeepLayer") u.role=PBWM2025UnitSpec::PFC_DEEP;
 else if(type=="RWPredLayer") u.role=PBWM2025UnitSpec::RW_PREDICTION;
 else if(type=="RWDaLayer") u.role=PBWM2025UnitSpec::RW_DOPAMINE;
 else if(type=="CINLayer") u.role=PBWM2025UnitSpec::CIN;
 const auto pb=l["pbwm"].toObject(),mx=l["matrix"].toObject(),gp=l["gpi"].toObject(),pm=l["pfc_maint"].toObject(),pg=l["pfc_gate"].toObject();
 u.d2_receptor=pb["DaR"].toString()=="D2R";u.maintenance_boundary=pb["MaintN"].toInt();u.maintenance_pools=pb["MaintX"].toInt();u.output_pools=pb["OutX"].toInt();
 u.patch_shunt=number(mx,"PatchShunt");u.burst_gain=number(mx,"BurstGain");u.dip_gain=number(mx,"DipGain");u.shunt_ach=mx["ShuntACh"].toBool();u.ach_inhibition=number(mx,"OutAChInhib");
 u.gate_cycle=gp["Cycle"].toInt();u.go_gain=number(gp,"GeGain");u.nogo_gain=number(gp,"NoGo");u.gate_threshold=number(gp,"Thr");u.threshold_act=gp["ThrAct"].toBool();
 u.output_gate=pg["OutGate"].toBool();u.output_q1_only=pg["OutQ1Only"].toBool();u.maintenance_gain=number(pm,"MaintGain");u.maximum_maintenance=pm["MaxMaint"].toInt();
 u.clear_fraction=number(pm,"Clear");u.output_clear_maintenance=pm["OutClearMaint"].toBool();u.use_dynamics=pm["UseDyn"].toBool();
 const auto dyns=l["pfc_dyns"].toArray();if(!dyns.empty()) {const auto d=dyns[0].toObject();u.dynamic_initial=number(d,"Init");u.dynamic_rise_tau=number(d,"RiseTau");u.dynamic_decay_tau=number(d,"DecayTau");}
 const QString quarters=(u.role==PBWM2025UnitSpec::PFC_DEEP?pg:gp)["GateQtr"].toString();u.gate_quarters=0;
 for(int q=1;q<=4;++q) if(quarters.contains(QString("Q%1").arg(q))) u.gate_quarters|=1<<(q-1);
 const auto rw=l["rw"].toObject()["PredRange"].toObject();u.prediction_min=number(rw,"Min");u.prediction_max=number(rw,"Max");u.reward_threshold=number(l["cin"].toObject(),"RewThr");
 u.UpdateAfterEdit_NoGui();
}
}
bool PBWM2025Network::LoadAuthoredModel(const String& filename) {
 QFile file(QString(filename));
 if(!file.open(QIODevice::ReadOnly)) {taMisc::Error("Cannot open PBWM2025 parameter export: ",filename);return false;}
 QJsonParseError error;const auto bytes=file.readAll();const auto document=QJsonDocument::fromJson(bytes,&error);
 if(error.error!=QJsonParseError::NoError||!document.isArray()) {taMisc::Error("Invalid PBWM2025 parameter export");return false;}
 const auto model=document.array();if(model.size()!=16) {taMisc::Error("SIR initial builder requires its authored16-layer topology");return false;}
 if(layers.leaves!=0) {taMisc::Error("LoadAuthoredModel requires an empty native network");return false;}
 authored_parameters=QString::fromUtf8(bytes);n_threads=1;times.quarter=25;times.cycle_qtr=false;SetNetFlag(NETIN_PER_PRJN);
 std::vector<LeabraLayer*> built;
 for(const auto& item:model) {
  const auto l=item.toObject();const String name=l["name"].toString();
  auto* layer=static_cast<LeabraLayer*>(FindMakeLayer(name));
  auto* us=static_cast<PBWM2025UnitSpec*>(FindMakeSpec(name+"Units",&TA_PBWM2025UnitSpec));
  auto* ls=static_cast<LeabraLayerSpec*>(FindMakeSpec(name+"Layer",&TA_LeabraLayerSpec));
  unit_parameters(*us,l);layer->SetUnitSpec(us);layer->SetLayerSpec(ls);
  layer->layer_type=us->role==PBWM2025UnitSpec::INPUT?Layer::INPUT:us->role==PBWM2025UnitSpec::TARGET?Layer::TARGET:Layer::HIDDEN;
  const auto shape=l["shape"].toObject()["Sizes"].toArray();
  if(shape.size()==4) {layer->unit_groups=true;layer->SetLayerUnitGeom(shape[3].toInt(),shape[2].toInt());layer->SetLayerUnitGpGeom(shape[1].toInt(),shape[0].toInt());}
  else layer->SetLayerUnitGeom(shape[1].toInt(),shape[0].toInt());
  const auto inhibition=l["inhib"].toObject();inhib_parameters(ls->lay_inhib,inhibition["Layer"].toObject());inhib_parameters(ls->unit_gp_inhib,inhibition["Pool"].toObject());
  const auto self=inhibition["Self"].toObject(),avg=inhibition["ActAvg"].toObject();
  ls->inhib_misc.self_fb=self["On"].toBool()?number(self,"Gi"):0.0f;ls->inhib_misc.self_tau=number(self,"Tau");ls->inhib_misc.thr_rel=false;ls->inhib_misc.net_thr=std::numeric_limits<float>::lowest();
  ls->avg_act.targ_init=number(avg,"Init");ls->avg_act.fixed=avg["Fixed"].toBool();ls->avg_act.use_ext_act=avg["UseExtAct"].toBool();ls->avg_act.use_first=avg["UseFirst"].toBool();ls->avg_act.tau=number(avg,"Tau");ls->avg_act.adjust=number(avg,"Adjust");
  const auto a=l["act"].toObject(),clamp=a["Clamp"].toObject();ls->decay.trial=number(a["Init"].toObject(),"Decay");ls->clamp.hard=clamp["Hard"].toBool();ls->clamp.gain=number(clamp,"Gain");ls->clamp.avg=clamp["Avg"].toBool();
  ls->UpdateAfterEdit_NoGui();layer->UpdateAfterEdit_NoGui();built.push_back(layer);
 }
 auto* full=static_cast<FullPrjnSpec*>(FindMakeSpec("Full",&TA_FullPrjnSpec));
 auto* one=static_cast<OneToOnePrjnSpec*>(FindMakeSpec("OneToOne",&TA_OneToOnePrjnSpec));
 auto* repeated=static_cast<OneToOnePrjnSpec*>(FindMakeSpec("OneToOneAcrossPools",&TA_OneToOnePrjnSpec));repeated->use_gp=true;
 auto* grouped=static_cast<GpOneToOnePrjnSpec*>(FindMakeSpec("PoolToPool",&TA_GpOneToOnePrjnSpec));
 for(int li=0;li<model.size();++li) {
  auto* recv=built[li];const auto paths=model[li].toObject()["paths"].toArray();
  for(const auto& entry:paths) {
   const auto path=entry.toObject();auto* send=FindLayer(String(path["send"].toString()));
   if(!send) return false;
   const int count=path["synapses"].toArray().size();ProjectionSpec* pattern=full;
   if(count!=send->n_units*recv->n_units) {
    if(path["send"].toString()=="CtrlInput") pattern=repeated;
    else if(send->unit_groups&&send->un_geom.n>1) pattern=grouped;
    else pattern=one;
   }
   auto* cs=static_cast<LeabraConSpec*>(FindMakeSpec(send->name+"To"+recv->name,&TA_LeabraConSpec));
   cs->learn=false;cs->rnd.mean=.5f;cs->rnd.var=0.0f;cs->wt_limits.sym=false;
   const auto scale=path["wt_scale"].toObject();cs->wt_scale.abs=number(scale,"Abs");cs->wt_scale.rel=number(scale,"Rel");cs->UpdateAfterEdit_NoGui();
   FindMakePrjn(recv,send,pattern,cs);
  }
 }
 Build();if(!IsBuiltIntact()) return false;
 Init_Weights();
 auto* state=static_cast<PBWM2025NetworkState_cpp*>(net_state);int total=0;
 for(int li=0;li<model.size();++li) {
  const auto paths=model[li].toObject()["paths"].toArray();auto* recv=built[li];
  for(const auto& entry:paths) {
   const auto path=entry.toObject();auto* send=FindLayer(String(path["send"].toString()));auto* prjn=FindMakePrjn(recv,send);
   const auto starts=path["send_starts"].toArray(),counts=path["send_counts"].toArray(),indices=path["send_indices"].toArray(),synapses=path["synapses"].toArray();
   for(int si=0;si<counts.size();++si) {
    auto* su=send->GetUnitState(state,si);auto* group=su->SendConState(state,prjn->send_idx);
    if(group->size!=counts[si].toInt()) {taMisc::Error("PBWM2025 native path count mismatch",send->name,recv->name);return false;}
    for(int j=0;j<group->size;++j) {
     const int target=group->UnState(j,state)->lay_un_idx;int source_index=-1;
     for(int k=0;k<counts[si].toInt();++k) {const int idx=starts[si].toInt()+k;if(indices[idx].toInt()==target) source_index=idx;}
     if(source_index<0) {taMisc::Error("PBWM2025 native indexed connection mismatch");return false;}
     const auto syn=synapses[source_index].toObject();group->Cn(j,LeabraConSpec_cpp::WT,state)=number(syn,"Wt");group->Cn(j,LeabraConSpec_cpp::FWT,state)=number(syn,"LWt");group->Cn(j,LeabraConSpec_cpp::SWT,state)=number(syn,"LWt");group->Cn(j,LeabraConSpec_cpp::DWT,state)=0.0f;group->Cn(j,LeabraConSpec_cpp::SCALE,state)=number(syn,"Scale");++total;
    }
   }
  }
 }
 if(total!=861||n_units!=96) {taMisc::Error("PBWM2025 authored graph size mismatch");return false;}
 state->InitializePBWMState();return true;
}
