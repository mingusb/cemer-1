#include "PBWM2025NetworkState_cpp.h"
#include "PBWM2025UnitSpec_cpp.h"
#include "PBWM2025FastExp.h"
#include <LeabraLayerSpec_cpp>
#include <LeabraPrjnState_cpp>
#include <algorithm>
#include <cmath>
#include <vector>

struct PBWM2025Gate {float activation=0.0f;bool now=false;int count=-1;};
struct PBWM2025Storage {
 std::vector<PBWM2025Gate> gates;
 std::vector<float> maintenance,maintenance_ge,learning_da,da,ach;
};
PBWM2025NetworkState_cpp::PBWM2025NetworkState_cpp():pbwm(new PBWM2025Storage) { }
PBWM2025NetworkState_cpp::~PBWM2025NetworkState_cpp() {delete pbwm;}
UnitSpec_cpp* PBWM2025NetworkState_cpp::NewUnitSpec(int type) const {
 if(type==N_LeabraUnitSpecs) return new PBWM2025UnitSpec_cpp;
 return inherited::NewUnitSpec(type);
}
void PBWM2025NetworkState_cpp::InitializePBWMState() {
 pbwm->gates.assign(n_ungps_built,{});
 pbwm->maintenance.assign(n_units_built,0.0f);pbwm->maintenance_ge.assign(n_units_built,0.0f);pbwm->learning_da.assign(n_units_built,0.0f);
 pbwm->da.assign(n_layers_built,0.0f);pbwm->ach.assign(n_layers_built,0.0f);
}
void PBWM2025NetworkState_cpp::Init_Acts() {inherited::Init_Acts();InitializePBWMState();}
void PBWM2025NetworkState_cpp::Trial_Init() {
 inherited::Trial_Init();
 // The authored layer-level modulators and PFC pool memory survive alpha initialization.
 for(int li=0;li<n_layers_built;++li) {
  auto* layer=GetLayerState(li);layer->hard_clamped=false;
  for(int i=0;i<layer->n_units;++i) {auto* u=layer->GetUnitState(this,i);u->da_p=pbwm->da[li];u->ach=pbwm->ach[li];}
 }
}
void PBWM2025NetworkState_cpp::Quarter_Init() {
 Quarter_Init_Counters();
 if(quarter==0) Compute_NetinScale();
 for(int li=0;li<n_layers_built;++li) {
  auto* layer=GetLayerState(li);layer->hard_clamped=false;
  if(quarter==3&&layer->layer_type==LayerState_cpp::TARGET) {
   for(int i=0;i<layer->n_units;++i) {auto* u=layer->GetUnitState(this,i);u->SetExtFlag(UnitState_cpp::EXT);u->ext=u->targ;}
  }
 }
}
namespace {
using US=PBWM2025UnitSpec_cpp;
float noisy_activation(LeabraActFunSpec_cpp& a,float x) {
 if(x<0.0f) {const float exponent=-(x*a.sig_gain_nvar);if(exponent>50.0f) return 0.0f;return a.sig_mult_eff/(1.0f+GoNxx1FastExp(exponent));}
 if(x<a.interp_range) {const float fraction=1.0f-((a.interp_range-x)/a.interp_range);return a.sig_val_at_0+fraction*a.interp_val;}
 return a.XX1GainCor(x);
}
US* spec(LeabraLayerState_cpp* layer,PBWM2025NetworkState_cpp* net) {return static_cast<US*>(layer->GetUnitSpec(net));}
int group_index(LeabraUnitState_cpp* u,PBWM2025NetworkState_cpp* net) {return u->GetOwnUnGp(net)->ungp_idx;}
void set_rate(LeabraUnitState_cpp* u,float activation) {u->act=u->act_eq=u->act_raw=activation;u->act_nd=activation;}
float profile_value(US* us,int count) {
 float value=us->dynamic_initial;const float time=static_cast<float>(count-1);
 if(time<=0.0f) return value;
 if(us->dynamic_rise_tau>0.0f&&us->dynamic_decay_tau>0.0f) {
  if(time>=us->dynamic_rise_tau) value=1.0f-((time-us->dynamic_rise_tau)/us->dynamic_decay_tau);
  else value=us->dynamic_initial+(1.0f-us->dynamic_initial)*(time/us->dynamic_rise_tau);
 } else if(us->dynamic_rise_tau>0.0f) value=us->dynamic_initial+(1.0f-us->dynamic_initial)*(time/us->dynamic_rise_tau);
 else if(us->dynamic_decay_tau>0.0f) value=us->dynamic_initial-us->dynamic_initial*(time/us->dynamic_decay_tau);
 return std::clamp(value,0.001f,1.0f);
}
}
void PBWM2025NetworkState_cpp::Cycle_Run() {
 if(n_thrs_built!=1) {StateError("PBWM2025 currently requires one CPU thread");return;}
 // Native indexed sender transport; keep receivers active even while externally clamped.
 Send_Netin_Thr(0);
 for(int li=0;li<n_layers_built;++li) {
  auto* layer=GetLayerState(li);auto* us=spec(layer,this);
  for(int ui=0;ui<layer->n_units;++ui) {
   auto* u=layer->GetUnitState(this,ui);float go=0.0f,nogo=0.0f;
   for(int g=0;g<u->NRecvConGps(this);++g) {
    auto* group=u->RecvConState(this,g);if(group->NotActive()) continue;
    const float delta=ThrSendNetinTmpPerPrjn(0,g)[u->flat_idx];
    group->net_raw+=delta;u->net_raw+=delta;
    if(us->role==US::GPI) {
     auto* sending=spec(group->GetSendLayer(this),this);
     if(sending->role==US::MATRIX&&!sending->d2_receptor) go=group->net_raw;else nogo=group->net_raw;
    }
   }
   if(us->role==US::GPI) u->net_raw=(us->go_gain+us->nogo_gain)*(go-us->nogo_gain*nogo);
   float raw=u->net_raw;if(us->role==US::PFC_DEEP) raw+=pbwm->maintenance_ge[u->flat_idx];
   u->net+=(us->dt.integ/us->dt.net_tau)*(raw-u->net);
   u->gi_syn+=(us->dt.integ/us->dt.net_tau)*(u->gi_raw-u->gi_syn);u->gi_syn=std::max(u->gi_syn,0.0f);
  }
 }
 InitCycleNetinTmp_Thr(0);
 Compute_NetinStats_Thr(0);Compute_NetinStats_Post();Compute_Inhib();
 // Ordered layer activation. CIN sees the preceding pool statistics; PFC and Matrix
 // see the preceding gate/DA broadcasts. New broadcasts occur after all statistics.
 for(int li=0;li<n_layers_built;++li) {
  auto* layer=GetLayerState(li);auto* us=spec(layer,this);auto* ls=layer->GetLayerSpec(this);
  for(int ui=0;ui<layer->n_units;++ui) {
   auto* u=layer->GetUnitState(this,ui);u->da_p=pbwm->da[li];u->ach=pbwm->ach[li];
   if(us->role==US::RW_PREDICTION) set_rate(u,std::clamp(u->net,us->prediction_min,us->prediction_max));
   else if(us->role==US::RW_DOPAMINE) {
    auto* reward=GetLayerState(us->reward_layer)->GetUnitState(this,0);auto* prediction=GetLayerState(us->prediction_layer)->GetUnitState(this,0);
    set_rate(u,reward->HasExtFlag(UnitState_cpp::EXT)?reward->act-prediction->act:0.0f);
   } else if(us->role==US::CIN) {
    float value=std::max(std::fabs(GetLayerState(us->reward_layer)->GetLayUnGpState(this)->acts.max),std::fabs(GetLayerState(us->prediction_layer)->GetLayUnGpState(this)->acts.max));
    if(us->reward_threshold>0.0f&&value>us->reward_threshold) value=1.0f;set_rate(u,value);
   } else {
    auto* group=u->GetOwnUnGp(this);us->Compute_ApplyInhib(u,this,0,layer,group->i_val.g_i);
    if(us->role==US::MATRIX&&us->ach_inhibition!=0.0f) {
     const int pool=ui/layer->un_geom_n;const int x=pool%layer->gp_geom_x;
     if(x>=us->maintenance_boundary) {float ach=u->ach;if(us->shunt_ach&&u->shunt>0.0f) ach*=us->patch_shunt;u->gc_i+=us->ach_inhibition*(1.0f-ach);}
    }
    const float ge=u->net*us->g_bar.e,gi=u->gc_i*us->g_bar.i;
    u->I_net=ge*(us->e_rev.e-u->v_m_eq)+us->g_bar.l*(us->e_rev.l-u->v_m_eq)+gi*(us->e_rev.i-u->v_m_eq);
    u->v_m_eq=std::clamp(u->v_m_eq+(us->dt.integ/us->dt.vm_tau)*u->I_net,us->vm_range.min,us->vm_range.max);u->v_m=u->v_m_eq;
    if(ls->clamp.hard&&u->HasExtFlag(UnitState_cpp::EXT)) {
     set_rate(u,std::clamp(u->ext,us->clamp_range.min,us->clamp_range.max));u->v_m=u->v_m_eq=us->act.thr+u->act/us->act.gain;u->da=0.0f;u->I_net=0.0f;
    } else {
     const float x=u->act<us->act.vm_act_thr&&u->v_m_eq<=us->act.thr?u->v_m_eq-us->act.thr:ge-us->Compute_EThresh(u);
     const float target=noisy_activation(us->act,x);const float old=u->act;const float next=old+(us->dt.integ/us->dt.vm_tau)*(target-old);set_rate(u,next);u->da=next-old;
    }
    if(us->role==US::MATRIX) {
     float da=u->da_p;if(u->shunt>0.0f) da*=us->patch_shunt;if(da>0.0f) da*=us->burst_gain;else da*=us->dip_gain;if(us->d2_receptor) da*=-1.0f;pbwm->learning_da[u->flat_idx]=da;
    }
   }
   us->Compute_SRAvg(u,this,0);
  }
  if(us->role==US::PFC_DEEP&&!(us->output_gate&&us->output_q1_only&&quarter>1)) {
   for(int g=0;g<layer->n_ungps;++g) {auto& gate=pbwm->gates[layer->GetUnGpState(this,g)->ungp_idx];if(!gate.now) continue;if(gate.activation>0.0f) gate.count=0;if(gate.count>=us->maximum_maintenance) gate.count=-1;}
  }
 }
 Compute_CycleStats_Thr(0);Compute_CycleStats_Post();
 for(int li=0;li<n_layers_built;++li) {
  auto* layer=GetLayerState(li);auto* us=spec(layer,this);
  if(us->role==US::RW_DOPAMINE) {const float da=layer->GetUnitState(this,0)->act;for(auto& value:pbwm->da) value=da;}
  else if(us->role==US::CIN) {const float ach=layer->GetUnitState(this,0)->act;for(int dest=0;dest<n_layers_built;++dest) if(spec(GetLayerState(dest),this)->role==US::MATRIX) pbwm->ach[dest]=ach;}
  else if(us->role==US::GPI) {
   for(int ui=0;ui<layer->n_units;++ui) {
    auto* u=layer->GetUnitState(this,ui);auto& gate=pbwm->gates[group_index(u,this)];
    if(quarter==0&&QuarterCycle()==0) gate.activation=0.0f;
    gate.now=(us->gate_quarters&(1<<quarter))&&QuarterCycle()==us->gate_cycle;
    if(gate.now) {if(u->act<us->gate_threshold) {gate.activation=0.0f;if(gate.count>=0) ++gate.count;else --gate.count;}else {gate.count=0;gate.activation=u->act;}}
   }
   for(int dest=0;dest<n_layers_built;++dest) {
    auto* receiver=GetLayerState(dest);auto* rs=spec(receiver,this);if(rs->role!=US::MATRIX&&rs->role!=US::PFC_DEEP) continue;
    for(int g=0;g<receiver->n_ungps;++g) {
     int source_group=g;if(rs->role==US::PFC_DEEP&&rs->output_gate) source_group+=us->maintenance_pools;
     auto& to=pbwm->gates[receiver->GetUnGpState(this,g)->ungp_idx];const auto& from=pbwm->gates[layer->GetUnGpState(this,source_group)->ungp_idx];to.activation=from.activation;to.now=from.now;
    }
   }
  }
 }
 for(int li=0;li<n_layers_built;++li) {
  auto* layer=GetLayerState(li);
  for(int ui=0;ui<layer->n_units;++ui) {auto* u=layer->GetUnitState(this,ui);const auto& gate=pbwm->gates[group_index(u,this)];u->thal=gate.activation;u->thal_gate=gate.now?1.0f:0.0f;u->thal_cnt=static_cast<float>(gate.count);if(gate.now) u->act_g=u->act;u->da_p=pbwm->da[li];u->ach=pbwm->ach[li];}
 }
 Cycle_IncrCounters();
}
void PBWM2025NetworkState_cpp::Quarter_Final() {
 // The fixed-weight milestone preserves the native quarter-recording API but
 // performs no DWt or weight update. Learning is a separate acceptance milestone.
 for(int li=0;li<n_layers_built;++li) {
  auto* layer=GetLayerState(li);auto* us=spec(layer,this);
  for(int ui=0;ui<layer->n_units;++ui) {auto* u=layer->GetUnitState(this,ui);us->Quarter_Final_RecVals(u,this,0);}
  if(us->role==US::PFC_DEEP&&(us->gate_quarters&(1<<quarter))) {
   for(int g=0;g<layer->n_ungps;++g) {auto& gate=pbwm->gates[layer->GetUnGpState(this,g)->ungp_idx];if(gate.count<0) --gate.count;else ++gate.count;}
   auto* superficial=GetLayerState(us->superficial_layer);
   for(int ui=0;ui<layer->n_units;++ui) {
    auto* u=layer->GetUnitState(this,ui);const auto& gate=pbwm->gates[group_index(u,this)];auto& maint=pbwm->maintenance[u->flat_idx];auto& ge=pbwm->maintenance_ge[u->flat_idx];
    if(gate.count<0) {maint=0.0f;ge=0.0f;}else if(gate.count<=1) maint=us->maintenance_gain*superficial->GetUnitState(this,ui)->act;
    ge=maint*(us->use_dynamics?profile_value(us,gate.count):1.0f);
   }
  }
 }
 Quarter_Final_Layers();Quarter_Final_Counters();
}
