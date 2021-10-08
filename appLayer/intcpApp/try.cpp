/*
g++ appLayer/in*App/try.cpp -o appLayer/in*App/try
appLayer/in*App/try
*/
#include <iostream>
#include <algorithm>
#include <vector>
using namespace std;
struct s{
    int l,r;
    s(int _l,int _r):l(_l),r(_r){}
    s(){}
    bool operator< (const s &a) const{
        return this->l<a.l;
    }
};
bool solution(vector<int> &A, vector<int> &P, int B, int E){
    if(B>E){
        int tmp=E;
        E=B;
        B=tmp;
    }
    s sv[100005];
    int n=A.size();
    for(int i=0;i<n;i++){
        sv[i] = s(P[i]-A[i],P[i]+A[i]);
    }
    sort(sv,sv+n);
    int last=0,next=0;
    s rm(B,0);
    while(1){
        last=next;
        next=upper_bound(sv+last,sv+n,rm)-sv;
        if(next<=0 || last==next){
            return false;
        }
        rm=sv[last];
        for(int i=last;i<next;i++){
            if(sv[i].r>rm.r){
                rm=sv[i];
            }
        }
        if(rm.r>=E)
            return true;
    }
    return false;
}
int main(){
    vector<int> a,p;
    a.push_back(2);
    a.push_back(1);
    p.push_back(5);
    p.push_back(1);
    int b=-1,e=2;
    cout<<solution(a,p,b,e)<<endl;
}